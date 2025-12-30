import onnxruntime as ort
from tokenizers import Tokenizer
import numpy as np
import logging

tokenizer = Tokenizer.from_file("onnx_model/tokenizer.json")

session = ort.InferenceSession(
    "onnx_model/model.onnx",
    providers=["CPUExecutionProvider"]
)

def _make_zero_array_for_input(inp, seq_len):
    """Create a zero array matching a reasonable shape for the input.
    Prefer (1, seq_len) for 2D inputs, else (1,) scalar fallback.
    """
    try:
        shape = inp.shape  # may contain symbolic dims or None
        # most token inputs are (batch, seq). batch is usually 1.
        if shape and len(shape) == 2:
            return np.zeros((1, seq_len), dtype=np.int64)
        elif shape and len(shape) == 1:
            return np.zeros((1,), dtype=np.int64)
    except Exception:
        pass
    return np.zeros((1,), dtype=np.int64)

def embed_text(text):
    tokens = tokenizer.encode(text)
    input_ids = np.array([tokens.ids], dtype=np.int64)
    attention_mask = np.ones_like(input_ids, dtype=np.int64)

    # Build ort_inputs by inspecting required ONNX inputs.
    ort_inputs = {}
    seq_len = input_ids.shape[1]

    # map easy names first (handle common variants)
    lower_inputs = {inp.name.lower(): inp for inp in session.get_inputs()}

    for inp in session.get_inputs():
        name = inp.name
        lname = name.lower()

        if "input_ids" in lname or "inputid" in lname:
            ort_inputs[name] = input_ids
            continue

        if "attention" in lname or "mask" in lname:
            ort_inputs[name] = attention_mask
            continue

        if "token_type" in lname or "segment_ids" in lname or "token-type" in lname:
            # token_type_ids are usually zeros for single-sequence inputs
            ort_inputs[name] = np.zeros_like(input_ids, dtype=np.int64)
            continue

        # fallback: produce zeros respecting shape hint (1, seq_len) when sensible
        ort_inputs[name] = _make_zero_array_for_input(inp, seq_len)

    # run inference
    outputs = session.run(None, ort_inputs)[0]
    pooled = outputs.mean(axis=1)[0]
    return pooled.tolist()
