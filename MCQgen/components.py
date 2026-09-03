import customtkinter as ctk

class SlidingViewManager(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.views = {}
        self.current_view_name = None
        self.is_animating = False

    def add_view(self, name, frame_cls, *args, **kwargs):
        """Register a view frame inside the container."""
        frame = frame_cls(self, *args, **kwargs)
        self.views[name] = frame
        return frame

    def show_view(self, name, direction="left", duration=200, steps=15):
        """
        Switches view with a smooth horizontal slide.
        direction='left' : Current slides left, new slides in from right.
        direction='right': Current slides right, new slides in from left.
        """
        if name not in self.views or self.current_view_name == name:
            return

        if self.is_animating:
            return  # Prevent animation collisions

        old_view = self.views.get(self.current_view_name)
        new_view = self.views[name]
        self.current_view_name = name

        # First view setup (No animation)
        if old_view is None:
            new_view.place(relx=0, rely=0, relwidth=1, relheight=1)
            return

        self.is_animating = True

        # Determine start/end positions based on slide direction
        if direction == "left":
            start_new_relx = 1.0
            end_old_relx = -1.0
        else:
            start_new_relx = -1.0
            end_old_relx = 1.0

        new_view.place(relx=start_new_relx, rely=0, relwidth=1, relheight=1)
        new_view.lift()  # Bring incoming frame to front

        step_delay = max(1, duration // steps)

        def _animate_step(step):
            progress = step / steps
            # Smooth ease-out curve
            eased_progress = 1 - (1 - progress) ** 2

            # Calculate positions
            old_x = end_old_relx * eased_progress
            new_x = start_new_relx * (1 - eased_progress)

            old_view.place(relx=old_x, rely=0, relwidth=1, relheight=1)
            new_view.place(relx=new_x, rely=0, relwidth=1, relheight=1)

            if step < steps:
                self.after(step_delay, lambda: _animate_step(step + 1))
            else:
                old_view.place_forget()  # Unmap old view once animation completes
                new_view.place(relx=0, rely=0, relwidth=1, relheight=1)
                self.is_animating = False

        _animate_step(1)
