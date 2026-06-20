#!/usr/bin/env python3
"""
Optional upgrade path (blueprint Section 5.3 / Appendix A): convert a
sentence-transformers embedding model or a Qwen3-Reranker to ONNX and apply INT8
dynamic quantization for a 2-3x CPU speedup.

This is NOT required to run rank.py — the default LSA backend needs no models.
It is provided so the heavier 2026 backends described in the blueprint are a
config change, not a rewrite. Run it once, offline (network allowed at this step).

    python onnx_optimize.py --model nomic-ai/nomic-embed-text-v1.5 --quantize int8

Requires the optional deps:  pip install sentence-transformers onnx onnxruntime optimum
"""
from __future__ import annotations

import argparse
import os
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="HF model id to export")
    ap.add_argument("--out", default="artifacts/onnx", help="output dir")
    ap.add_argument("--quantize", choices=["none", "int8"], default="int8")
    args = ap.parse_args()

    try:
        from optimum.onnxruntime import ORTModelForFeatureExtraction
        from optimum.onnxruntime.configuration import AutoQuantizationConfig
        from optimum.onnxruntime import ORTQuantizer
        from transformers import AutoTokenizer
    except Exception:
        print("[onnx_optimize] optional deps missing. Install with:\n"
              "  pip install sentence-transformers onnx onnxruntime optimum",
              file=sys.stderr)
        sys.exit(2)

    os.makedirs(args.out, exist_ok=True)
    print(f"[onnx_optimize] exporting {args.model} -> {args.out} (ONNX)")
    model = ORTModelForFeatureExtraction.from_pretrained(args.model, export=True)
    tok = AutoTokenizer.from_pretrained(args.model)
    model.save_pretrained(args.out)
    tok.save_pretrained(args.out)

    if args.quantize == "int8":
        print("[onnx_optimize] applying INT8 dynamic quantization ...")
        quantizer = ORTQuantizer.from_pretrained(args.out)
        qconfig = AutoQuantizationConfig.avx2(is_static=False, per_channel=False)
        quantizer.quantize(save_dir=args.out, quantization_config=qconfig)
    print(f"[onnx_optimize] done -> {args.out}")


if __name__ == "__main__":
    main()
