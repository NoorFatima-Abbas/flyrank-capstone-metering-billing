API_CALL_MICROS = 1_000
INPUT_PER_MTOK = 300_000
CACHED_PER_MTOK = 75_000
OUTPUT_PER_MTOK = 2_500_000
MTOK = 1_000_000


def token_cost_micros(input_tokens: int, cached_input_tokens: int, output_tokens: int, reasoning_tokens: int) -> int:
    fresh = input_tokens - cached_input_tokens
    if fresh < 0:
        raise ValueError("cached_input_tokens cannot exceed input_tokens")
    total = (
        fresh * INPUT_PER_MTOK
        + cached_input_tokens * CACHED_PER_MTOK
        + (output_tokens + reasoning_tokens) * OUTPUT_PER_MTOK
    )
    return (total + MTOK // 2) // MTOK