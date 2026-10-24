"""The same Library interactions on desktop and Android, with optional captures."""
import re
import time


class LibraryReaderCases:
    def __init__(self, driver, chapter_text, log_text=lambda: "", capture=lambda name: None):
        self.driver = driver
        self.chapter_text = chapter_text
        self.log_text = log_text
        self.capture = capture

    def open_library(self):
        self.driver.press(label="Library", role="button")
        self.driver.wait_idle(frames=3)
        downloads = self.driver.find(label="Download", role="button", visible=True)
        if downloads:
            self.driver.press(key=downloads[-1]["key"], role="button")
            self.driver.wait(label="Open", role="button", timeout=60)
        if self.driver.find(label="Open", role="button", visible=True):
            self.driver.press(label="Open", role="button")
        self.driver.wait(label="Tao Te Ching", role="button", timeout=60)

    def page_label(self):
        self.driver.wait(key=27511)
        labels = [label for label in self.driver.labels() if re.fullmatch(r"\d+ / \d+", label)]
        assert len(labels) == 1, self.driver.text()
        return labels[0]

    def page_number(self):
        return int(self.page_label().split(" / ")[0])

    def page_text(self):
        return self.driver.wait(key=27502)["label"]

    def wait_page(self, number):
        deadline = time.monotonic() + 20
        while self.page_number() != number:
            assert time.monotonic() < deadline, (number, self.driver.text())
            time.sleep(.05)

    def open_tools(self, tab=None):
        self.driver.press(label=tab or "Annotations", role="button")
        assert not self.driver.find(role="modal"), "Reader tools opened a modal"

    def close_tools(self):
        self.driver.press(label="Close", role="button")
        self.driver.wait_idle(frames=3)

    def press_chapter(self, number):
        for _ in range(14):
            matches = self.driver.find(label=str(number), role="button", visible=True)
            if matches:
                self.driver.press(label=str(number), role="button")
                return
            self.driver.pointer(*self.driver.center(self.driver.wait(key=27605)), wheel=-3)
            self.driver.release_pointer()
            self.driver.wait_idle(frames=3)
        raise AssertionError(("Chapter not visible", number, self.driver.text()))

    def exercise(self):
        self.driver.press(label="Apps", role="button")
        self.open_library()
        self.driver.wait(label="Tao Te Ching", role="button")
        self.driver.wait(label="Tao Te Ching", role="text")
        self.driver.wait(label="Lao Tzu", role="text")
        assert not self.driver.find(label="Library", role="title_bar"), "Library still has a title bar"
        assert not self.driver.find(label="Start reading"), self.driver.text()
        assert "the local bundle cannot run" not in self.log_text()
        self.capture("shelf")
        self.driver.press(label="Tao Te Ching", role="button")
        self.capture("opening")
        self.driver.wait_gone(key=27800)
        first = self.page_text()
        assert self.chapter_text(1).startswith(first), first
        initial_total = int(self.page_label().split(" / ")[1])
        assert initial_total >= 81
        self.driver.wait_gone(label="Apps", role="button")
        # Page gestures and desktop arrows use the same page index.
        area = self.driver.wait(key=27502)
        left = area["visible_x"] + area["visible_width"] * .12
        right = area["visible_x"] + area["visible_width"] * .88
        middle = area["visible_y"] + area["visible_height"] / 2
        self.driver.drag((right, middle), (left, middle))
        self.wait_page(2)
        self.capture("reader")
        self.driver.drag((left, middle), (right, middle))
        self.wait_page(1)
        self.driver.key("right")
        self.wait_page(2)
        self.driver.key("left")
        self.wait_page(1)
        assert not self.driver.find(label="Next chapter"), self.driver.text()
        theme_before = self.driver.wait(key=27704)["label"]
        self.driver.press(key=27704, role="button")
        theme_after = self.driver.wait(key=27704)["label"]
        assert theme_after != theme_before, "Book theme did not change"
        self.capture("reader-light" if theme_after == "Dark" else "reader-dark")
        # Open contents inside the one reader panel; jump to a longer chapter.
        self.open_tools("Contents")
        self.press_chapter(39)
        assert self.chapter_text(39).startswith(self.page_text()), self.page_text()
        before = self.page_number()
        self.driver.key("right")
        self.wait_page(before + 1)
        saved_page, saved_text = self.page_label(), self.page_text()
        # Highlight and multiline note are stored by text range in account records.
        self.page_text_snapshot = self.page_text()
        self.open_tools("Annotations")
        self.capture("tools")
        self.driver.press(focus_id=27619, role="text_area")
        self.driver.key("home")
        start_cursor = self.driver.wait(focus_id=27619)["cursor"]
        for _ in range(12):
            self.driver.key("right", shift=True)
        selection = self.driver.wait(focus_id=27619)
        assert 0 < selection["cursor"] - start_cursor < len(self.page_text_snapshot)
        self.driver.press(label="Highlight selection", role="toggle")
        self.driver.press(focus_id=27621, role="text_area")
        self.driver.type("A quiet passage.")
        self.driver.key("enter")
        self.driver.type("Remember the water.")
        self.driver.wait(value="A quiet passage.\nRemember the water.", role="text_area")
        self.capture("annotation")
        self.close_tools()
        self.capture("annotated-reader")
        self.driver.press(label="Back", role="button")
        self.driver.wait(label="Tao Te Ching", role="button")
        self.driver.press(label="Tao Te Ching", role="button")
        assert self.page_label() == saved_page and self.page_text() == saved_text
        self.open_tools("Annotations")
        self.driver.wait(value="A quiet passage.\nRemember the water.", role="text_area")
        assert self.driver.wait(label="Highlight selection", role="toggle")["selected"]
        self.close_tools()
        # Font changes reflow from the saved text position; repeat changes give
        # the same page count and never discard the anchored annotations.
        self.open_tools("Font")
        for _ in range(5):
            self.driver.press(label="+", role="button")
        self.close_tools()
        large_total = int(self.page_label().split(" / ")[1])
        assert large_total > initial_total, (initial_total, large_total)
        self.open_tools("Font")
        for _ in range(5):
            self.driver.press(label="-", role="button")
        self.close_tools()
        assert self.page_label() == saved_page and self.page_text() == saved_text
        self.open_tools("Annotations")
        self.driver.wait(value="A quiet passage.\nRemember the water.", role="text_area")
        assert self.driver.wait(label="Highlight selection", role="toggle")["selected"]
        self.close_tools()
        self.open_tools("Font")
        self.driver.press(key=27631)
        self.driver.press(label="Noto Sans", role="selectable")
        self.close_tools()
        assert self.driver.wait(key=27502)["hidden_lines"] == 0
        self.open_tools("Font")
        self.driver.press(key=27631)
        self.driver.press(label="System font", role="selectable")
        self.close_tools()
        assert self.page_label() == saved_page and self.page_text() == saved_text
        self.open_tools("Layout")
        for _ in range(2):
            self.driver.press(label="+", role="button", index=0)
            self.driver.press(label="+", role="button", index=1)
        self.close_tools()
        assert self.driver.wait(key=27502)["hidden_lines"] == 0
        self.open_tools("Layout")
        for _ in range(2):
            self.driver.press(label="-", role="button", index=0)
            self.driver.press(label="-", role="button", index=1)
        self.close_tools()
        assert self.page_label() == saved_page and self.page_text() == saved_text
        return {"page": saved_page, "text": saved_text, "theme": theme_after}

    def resume(self, saved):
        self.driver.press(label="Apps", role="button")
        self.open_library()
        self.driver.press(label="Tao Te Ching", role="button")
        assert self.page_label() == saved["page"] and self.page_text() == saved["text"]
        assert self.driver.wait(key=27704)["label"] == saved["theme"], "Book theme was lost after restart"
        self.open_tools("Annotations")
        self.driver.wait(value="A quiet passage.\nRemember the water.", role="text_area")
        assert self.driver.wait(label="Highlight selection", role="toggle")["selected"]
        self.close_tools()
        self.driver.press(label="Back", role="button")
        self.driver.wait(label="Tao Te Ching", role="button")
        self.driver.press(label="Back", role="button")
        self.driver.wait(label="Library", role="button")
