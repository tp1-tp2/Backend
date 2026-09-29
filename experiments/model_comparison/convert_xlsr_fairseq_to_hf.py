#!/usr/bin/env python
"""Converts a QuechuaBase XLS-R fairseq CTC checkpoint (checkpoint_best.pt) into a
HuggingFace Wav2Vec2ForCTC directory, WITHOUT needing fairseq installed.

Why not transformers' own conversion script: it imports fairseq, which doesn't
install cleanly on modern Python/torch. The checkpoint pickles fairseq config
classes, so a stub unpickler replaces them — only the tensors and plain config
values are needed.

Two model facts the conversion must preserve (both read from the checkpoint's own
config, not assumed):
  - task.normalize=True: the model was trained on zero-mean/unit-variance audio.
    Saved as preprocessor do_normalize=True.
  - The fairseq dictionary order (<s>=0 is the CTC blank, <unk>=3 is emitted as
    the word boundary — see QuechuaBase/asr-puno-quechua inference/transcribe.py).
    Saved verbatim as vocab_fairseq.json; decode with decode_ctc(), not the HF
    tokenizer, which assumes a different blank/delimiter layout.

Usage:
    python convert_xlsr_fairseq_to_hf.py --ckpt E:/asr-models/xls-r-cpt-qxp-silver/checkpoint_best.pt \
        --dict E:/asr-models/xls-r-cpt-qxp-silver/dict.ltr.txt --out E:/asr-models/xls-r-cpt-qxp-silver-hf
"""
import argparse
import ast
import json
import pickle
import re
import types
from pathlib import Path

import torch
from transformers import Wav2Vec2Config, Wav2Vec2FeatureExtractor, Wav2Vec2ForCTC

FAIRSEQ_SPECIALS = ["<s>", "<pad>", "</s>", "<unk>"]


class _Stub:
    def __init__(self, *args, **kwargs):
        self._args = args

    def __setstate__(self, state):
        self.__dict__["_state"] = state


class _FairseqSafeUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if module.startswith("fairseq"):
            return type(name, (_Stub,), {})
        return super().find_class(module, name)


_safe_pickle = types.ModuleType("fairseq_safe_pickle")
_safe_pickle.Unpickler = _FairseqSafeUnpickler
_safe_pickle.load = pickle.load


def load_fairseq_checkpoint(path: str) -> dict:
    return torch.load(path, map_location="cpu", weights_only=False, pickle_module=_safe_pickle)


def _eval_layer_spec(expr: str):
    """fairseq eval()s conv_feature_layers (e.g. "[(512,10,5)] + [(512,3,2)] * 4");
    evaluate only list/tuple/number literals combined with + and * instead."""
    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, (ast.List, ast.Tuple)):
            items = [ev(e) for e in node.elts]
            return items if isinstance(node, ast.List) else tuple(items)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mult)):
            left, right = ev(node.left), ev(node.right)
            return left + right if isinstance(node.op, ast.Add) else left * right
        raise ValueError(f"Unsupported node in conv_feature_layers: {ast.dump(node)}")
    return ev(ast.parse(expr, mode="eval"))


def build_config(w2v: dict, vocab_size: int) -> Wav2Vec2Config:
    conv_layers = _eval_layer_spec(w2v["conv_feature_layers"])
    return Wav2Vec2Config(
        vocab_size=vocab_size,
        hidden_size=w2v["encoder_embed_dim"],
        num_hidden_layers=w2v["encoder_layers"],
        num_attention_heads=w2v["encoder_attention_heads"],
        intermediate_size=w2v["encoder_ffn_embed_dim"],
        hidden_act=w2v["activation_fn"],
        feat_extract_norm="layer" if w2v["extractor_mode"] == "layer_norm" else "group",
        feat_extract_activation="gelu",
        conv_dim=tuple(c[0] for c in conv_layers),
        conv_kernel=tuple(c[1] for c in conv_layers),
        conv_stride=tuple(c[2] for c in conv_layers),
        conv_bias=bool(w2v["conv_bias"]),
        num_conv_pos_embeddings=w2v["conv_pos"],
        num_conv_pos_embedding_groups=w2v["conv_pos_groups"],
        do_stable_layer_norm=bool(w2v["layer_norm_first"]),
        layer_norm_eps=1e-5,
        pad_token_id=0,
        ctc_loss_reduction="mean",
    )


def map_key(k: str, pos_g: str, pos_v: str) -> str:
    if k.startswith("w2v_encoder.proj."):
        return "lm_head." + k.split(".")[-1]
    k = k.removeprefix("w2v_encoder.w2v_model.")
    p = "wav2vec2."
    if k == "mask_emb":
        return p + "masked_spec_embed"
    if m := re.fullmatch(r"feature_extractor\.conv_layers\.(\d+)\.0\.(weight|bias)", k):
        return f"{p}feature_extractor.conv_layers.{m[1]}.conv.{m[2]}"
    if m := re.fullmatch(r"feature_extractor\.conv_layers\.(\d+)\.2\.1\.(weight|bias)", k):
        return f"{p}feature_extractor.conv_layers.{m[1]}.layer_norm.{m[2]}"
    if m := re.fullmatch(r"post_extract_proj\.(weight|bias)", k):
        return f"{p}feature_projection.projection.{m[1]}"
    if m := re.fullmatch(r"layer_norm\.(weight|bias)", k):
        return f"{p}feature_projection.layer_norm.{m[1]}"
    if k == "encoder.pos_conv.0.bias":
        return p + "encoder.pos_conv_embed.conv.bias"
    if k == "encoder.pos_conv.0.weight_g":
        return p + pos_g
    if k == "encoder.pos_conv.0.weight_v":
        return p + pos_v
    if m := re.fullmatch(r"encoder\.layer_norm\.(weight|bias)", k):
        return f"{p}encoder.layer_norm.{m[1]}"
    if m := re.fullmatch(r"encoder\.layers\.(\d+)\.(.+)", k):
        n, rest = m[1], m[2]
        rest = (rest.replace("self_attn_layer_norm", "layer_norm")
                    .replace("self_attn.", "attention.")
                    .replace("fc1", "feed_forward.intermediate_dense")
                    .replace("fc2", "feed_forward.output_dense"))
        return f"{p}encoder.layers.{n}.{rest}"
    raise KeyError(f"Unmapped fairseq key: {k}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--dict", required=True, help="fairseq dict.ltr.txt")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    ckpt = load_fairseq_checkpoint(args.ckpt)
    cfg = ckpt["cfg"]
    w2v = dict(cfg["model"]["w2v_args"]["model"])
    normalize = bool(cfg["task"]["normalize"])
    sd = ckpt["model"]

    symbols = FAIRSEQ_SPECIALS + [line.split()[0] for line in Path(args.dict).read_text(encoding="utf-8").splitlines() if line.strip()]
    vocab_size = sd["w2v_encoder.proj.weight"].shape[0]
    assert len(symbols) == vocab_size, f"dict has {len(symbols)} symbols, checkpoint head has {vocab_size}"

    model = Wav2Vec2ForCTC(build_config(w2v, vocab_size)).eval()
    hf_keys = set(model.state_dict().keys())
    pos_prefix = "encoder.pos_conv_embed.conv."
    if f"wav2vec2.{pos_prefix}parametrizations.weight.original0" in hf_keys:
        pos_g, pos_v = pos_prefix + "parametrizations.weight.original0", pos_prefix + "parametrizations.weight.original1"
    else:
        pos_g, pos_v = pos_prefix + "weight_g", pos_prefix + "weight_v"

    new_sd = {map_key(k, pos_g, pos_v): v for k, v in sd.items()}
    missing, unexpected = hf_keys - new_sd.keys(), new_sd.keys() - hf_keys
    assert not missing and not unexpected, f"missing={sorted(missing)[:5]} unexpected={sorted(unexpected)[:5]}"
    ref = model.state_dict()
    bad = [k for k, v in new_sd.items() if ref[k].shape != v.shape]
    assert not bad, f"shape mismatch: {bad[:5]}"
    model.load_state_dict(new_sd, strict=True)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out, safe_serialization=True)
    Wav2Vec2FeatureExtractor(
        feature_size=1, sampling_rate=16000, padding_value=0.0,
        do_normalize=normalize, return_attention_mask=True,
    ).save_pretrained(out)
    (out / "vocab_fairseq.json").write_text(json.dumps(symbols, ensure_ascii=False), encoding="utf-8")
    n_params = sum(v.numel() for v in new_sd.values())
    print(f"Converted {len(new_sd)} tensors ({n_params/1e6:.1f}M params), normalize={normalize}, vocab={vocab_size} -> {out}")


def decode_ctc(logits: torch.Tensor, symbols: list[str]) -> str:
    """Greedy CTC decode mirroring QuechuaBase's own inference/transcribe.py:
    collapse repeats, drop blank (<s>, index 0), map <unk> and | to spaces."""
    ids = logits.argmax(dim=-1).tolist()
    out, prev = [], None
    for i in ids:
        if i != prev and i != 0:
            out.append(symbols[i])
        prev = i
    text = "".join(out).replace("<unk>", " ").replace("|", " ")
    return re.sub(r"\s+", " ", text).strip()


if __name__ == "__main__":
    main()
