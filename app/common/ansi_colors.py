class ANSIColors:
    RESET = "\033[0m"
    RED = "\033[1;31m"
    CYAN = "\033[1;36m"
    BLUE = "\033[1;34m"
    GREEN = "\033[1;32m"

    @staticmethod
    def color_text(text, color):
        return f"{color}{text}{ANSIColors.RESET}"
