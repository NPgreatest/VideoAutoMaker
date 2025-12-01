class LLMError(RuntimeError):
    pass

class LLMHTTPError(LLMError):
    def __init__(self, status: int, text: str):
        super().__init__(f"HTTP {status}: {text}")
        self.status = status
        self.text = text

class LLMConfigError(LLMError):
    pass
