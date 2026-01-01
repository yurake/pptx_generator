class PrepareCommandError(Exception):
    """エラー種別に応じて CLI へ exit code を伝えるための例外。"""

    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code
