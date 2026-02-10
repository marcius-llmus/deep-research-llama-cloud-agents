import tiktoken


class TokenCountingService:
    """A centralized service for counting tokens using tiktoken with a generic model."""

    # Use cl100k_base which is the encoding for gpt-4, gpt-3.5-turbo, and text-embedding-ada-002.
    # It's a robust, general-purpose tokenizer.
    _tokenizer = tiktoken.get_encoding("cl100k_base")

    @staticmethod
    def count_tokens(text: str) -> int:
        """Counts the number of tokens in a string using a generic tokenizer."""

        if not text:
            return 0
        return len(TokenCountingService._tokenizer.encode(text, disallowed_special=()))

    @staticmethod
    def truncate_text(text: str, max_tokens: int) -> str:
        """Truncates a string to a maximum number of tokens."""

        if not text:
            return ""
        tokens = TokenCountingService._tokenizer.encode(text, disallowed_special=())
        if len(tokens) > max_tokens:
            truncated_tokens = tokens[:max_tokens]
            return TokenCountingService._tokenizer.decode(truncated_tokens)
        return text

