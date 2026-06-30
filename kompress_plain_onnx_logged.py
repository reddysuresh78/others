
"""Lightweight ONNX-only Kompress implementation for plain-text compression
with detailed logging.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import time
from dataclasses import dataclass
from typing import Any, List, Union
from langchain_community.document_loaders import PyPDFLoader
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s:%(lineno)d - %(message)s",
)
logger = logging.getLogger(__name__)

try:
    import onnxruntime as ort
    from transformers import AutoTokenizer
except Exception as exc:
    raise ImportError("onnxruntime and transformers are required") from exc


@dataclass
class PlainKompressResult:
    compressed: str
    original: str
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float


class PlainOnnxKompress:
    def __init__(
        self,
        onnx_path: Union[str, Path],
        tokenizer_name: Union[str, Path] = "answerdotai/ModernBERT-base",
        chunk_words: int = 350,
        score_threshold: float = 0.5,
    ) -> None:
        self.onnx_path = Path(onnx_path).expanduser()
        if not self.onnx_path.is_file():
            raise FileNotFoundError(f"ONNX model not found: {self.onnx_path}")

        tokenizer_source: Union[str, Path]
        tokenizer_source = Path(tokenizer_name).expanduser() if Path(tokenizer_name).exists() else tokenizer_name
        self.chunk_words = chunk_words
        self.score_threshold = score_threshold

        logger.info("Loading ONNX model: %s", self.onnx_path)

        sess_opts = ort.SessionOptions()
        sess_opts.intra_op_num_threads = 1
        sess_opts.inter_op_num_threads = 1

        self._session = ort.InferenceSession(
            str(self.onnx_path),
            sess_options=sess_opts,
            providers=["CPUExecutionProvider"],
        )

        logger.info("ONNX session created successfully")
        logger.debug("Providers: %s", self._session.get_providers())

        logger.debug("Model inputs:")
        for inp in self._session.get_inputs():
            logger.debug("  %s shape=%s type=%s", inp.name, inp.shape, inp.type)

        logger.debug("Model outputs:")
        for out in self._session.get_outputs():
            logger.debug("  %s shape=%s type=%s", out.name, out.shape, out.type)

        logger.info("Loading tokenizer: %s", tokenizer_source)
        self.tokenizer = AutoTokenizer.from_pretrained(
            tokenizer_source,
            local_files_only=True,
        )
        logger.info("Tokenizer loaded")

    def _run_onnx(self, input_ids: Any, attention_mask: Any) -> np.ndarray:
        logger.debug(
            "Calling ONNX runtime. input_ids=%s attention_mask=%s",
            input_ids.shape,
            attention_mask.shape,
        )

        start = time.perf_counter()

        scores = self._session.run(
            ["final_scores"],
            {
                "input_ids": np.asarray(input_ids, dtype=np.int64),
                "attention_mask": np.asarray(attention_mask, dtype=np.int64),
            },
        )[0]

        elapsed = (time.perf_counter() - start) * 1000

        logger.debug("ONNX inference executed in %.2f ms", elapsed)
        logger.debug("Output shape: %s", scores.shape)
        logger.debug(
            "Score stats: min=%.5f max=%.5f mean=%.5f",
            float(scores.min()),
            float(scores.max()),
            float(scores.mean()),
        )

        return scores

    def compress(self, content: str) -> PlainKompressResult:
        words = content.split()
        n_words = len(words)

        logger.info(
            "Compressing %d words (chunk=%d threshold=%.2f)",
            n_words,
            self.chunk_words,
            self.score_threshold,
        )

        if n_words < 10:
            logger.info("Too short to compress.")
            return PlainKompressResult(content, content, n_words, n_words, 1.0)

        kept_ids = set()

        for chunk_start in range(0, n_words, self.chunk_words):
            chunk = words[chunk_start:chunk_start + self.chunk_words]

            logger.debug(
                "Processing chunk starting at %d (%d words)",
                chunk_start,
                len(chunk),
            )

            t0 = time.perf_counter()

            encoding = self.tokenizer(
                chunk,
                is_split_into_words=True,
                truncation=True,
                max_length=512,
                padding=True,
                return_tensors="np",
            )

            logger.debug(
                "Tokenization took %.2f ms",
                (time.perf_counter() - t0) * 1000,
            )

            input_ids = encoding["input_ids"]
            attention_mask = encoding["attention_mask"]
            word_ids = encoding.word_ids(batch_index=0)

            logger.debug(
                "Tokenizer output shapes: input_ids=%s attention_mask=%s",
                input_ids.shape,
                attention_mask.shape,
            )

            scores = self._run_onnx(input_ids, attention_mask)[0]

            word_scores = {}

            for token_idx, wid in enumerate(word_ids):
                if wid is None:
                    continue
                score = float(scores[token_idx])
                if wid not in word_scores or score > word_scores[wid]:
                    word_scores[wid] = score
            for wid in sorted(word_scores):
                score = word_scores[wid]
                keep = score > self.score_threshold
                if keep:
                    kept_ids.add(chunk_start + wid)

        logger.info("Words kept: %d/%d", len(kept_ids), n_words)

        if not kept_ids:
            logger.warning("No words exceeded threshold.")
            return PlainKompressResult(content, content, n_words, n_words, 1.0)

        compressed_words = [words[i] for i in sorted(kept_ids)]
        compressed = " ".join(compressed_words)

        logger.info(
            "Compression ratio: %.3f (%d -> %d)",
            len(compressed_words) / n_words,
            n_words,
            len(compressed_words),
        )

        return PlainKompressResult(
            compressed=compressed,
            original=content,
            original_tokens=n_words,
            compressed_tokens=len(compressed_words),
            compression_ratio=len(compressed_words) / n_words,
        )

    def compress_batch(self, contents: List[str]) -> List[PlainKompressResult]:
        return [self.compress(c) for c in contents]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("onnx_path")
    parser.add_argument(
        "--tokenizer",
        default="answerdotai/ModernBERT-base",
        help="Tokenizer repo id or local tokenizer snapshot directory.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable DEBUG logging.",
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    comp = PlainOnnxKompress(args.onnx_path, tokenizer_name=args.tokenizer)

    loader = PyPDFLoader("LangChain.pdf")
    documents = loader.load()
    print(documents, len(documents))
    print("=" * 60)
    doc_text = "\n".join([doc.page_content for doc in documents])
    print(doc_text, len(doc_text))
    print("=" * 60)
    print(doc_text.split(), len(doc_text.split()))
    res = comp.compress(doc_text)

    print()
    print("=" * 60)
    print("Original words   :", res.original_tokens)
    print("Compressed words :", res.compressed_tokens)
    print("Ratio            :", f"{res.compression_ratio:.3f}")
    print("=" * 60)
    print(res.compressed)


if __name__ == "__main__":
    main()
