import customtkinter as ctk

class BasePage(ctk.CTkFrame):
    def __init__(self, parent, controller, show_back_button=True):
        super().__init__(parent)
        self.controller = controller

        if show_back_button:
            self.back_btn = ctk.CTkButton(self, text="← Back", width=60, height=24, fg_color="gray", hover_color="#555", command=self.controller.go_back)
            self.back_btn.place(x=10, y=10)

    def tkraise(self, *args, **kwargs):
        super().tkraise(*args, **kwargs)
        self.on_show()

    def on_show(self):
        """Called when the page is shown. Override this to refresh data."""
        if hasattr(self, 'back_btn'):
            self.back_btn.lift()
