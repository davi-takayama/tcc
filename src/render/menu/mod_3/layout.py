import pygame
from pygame import Rect, Surface
from pygame.event import Event

from ...staff import Staff
from ....utils.image_rescaler import ImageRescaler
from ....utils.module_model import ModuleClass
from ....utils.save_operations.read_save import Module


class Module3(ModuleClass):

    def __init__(
            self,
            screen: Surface,
            staff: Staff,
            change_state: classmethod,
            x_pos: int,
            width: int,
            module: Module,
    ) -> None:
        super().__init__(screen, staff, change_state, x_pos, width, module)
        self.text = self.generate_text(module, "Teste")
        self.note_y_placement = [
            self.staff.c3_position
            - (i * self.staff.line_spacing)
            - self.staff.line_spacing
            for i in range(5)
        ]
        self.note_x_placement = self.calculate_note_x_placements(width, 9)
        self.first_chord_rect: Rect = self.calculate_rect(self.note_x_placement[0], self.note_y_placement[2], 3)

    def __draw_star(self, x: int, y: int, chapter_index: int):
        if self.module.chapters[chapter_index]["completed"]:
            star_asset = self.full_star if self.module.chapters[chapter_index]["perfected"] else self.blank_star
            star_height = 16
            star_asset = ImageRescaler.rescale_from_height(star_asset, star_height)
            star_x = x + star_asset.get_width() // 10
            star_y = y + self.staff.line_spacing
            self.surface.blit(star_asset, (star_x, star_y))

    def render(self):
        self.surface.fill("white")
        self.__render_first_chord()
        self.note_renderer.quarter(
            x_pos=self.note_x_placement[1],
            y_pos=self.note_y_placement[0],
            color=("black" if self.module.chapters[0]["unlocked"] else "gray"),
        )

        self.__render_second_chord()
        self.note_renderer.eighth(
            [
                (self.note_x_placement[3], self.note_y_placement[1]),
                (self.note_x_placement[4], self.note_y_placement[2]),
            ],
            color=[
                ("black" if self.module.chapters[1]["unlocked"] else "gray"),
                ("black" if self.module.chapters[2]["unlocked"] else "gray"),
            ],
        )

        pygame.draw.line(self.surface, "black",
                         (self.note_x_placement[5], self.staff.line_positions[0]),
                         (self.note_x_placement[5], self.staff.line_positions[-1]),
                         5
                         )

        self.__render_third_chord()

        self.note_renderer.quarter(self.note_x_placement[7], self.note_y_placement[-2],
                                   color="black" if self.module.chapters[3]["unlocked"] else "gray")

        self.note_renderer.quarter(self.note_x_placement[8], self.note_y_placement[-3],
                                   color="black" if self.module.chapters[4]["unlocked"] else "gray")

        self.__draw_star(self.note_x_placement[1], self.note_y_placement[0], 0)
        self.__draw_star(self.note_x_placement[3], self.note_y_placement[1], 1)
        self.__draw_star(self.note_x_placement[4], self.note_y_placement[2], 2)
        self.__draw_star(self.note_x_placement[7], self.note_y_placement[-2], 3)
        self.__draw_star(self.note_x_placement[8], self.note_y_placement[-3], 4)

        text = pygame.font.Font(None, size=32).render(self.text, True, "black")
        text_x = (self.surface.get_width() - text.get_width()) // 2
        text_y = self.screen.get_height() // 4
        self.surface.blit(text, (text_x, text_y))

        self.screen.blit(self.surface, (self.x_pos, 0))

    def event_check(self, event_arg: Event | None = None):
        pass

    def __render_first_chord(self):
        for i in range(3):
            self.note_renderer.quarter(
                x_pos=self.note_x_placement[0],
                y_pos=self.note_y_placement[i],
                color=("black" if self.module.unlocked else "gray"),
            )
        star_asset = (
            self.blank_star
            if self.perfected_chapters != self.total_chapters
            else self.full_star
        )
        star_height = 30
        star_asset = ImageRescaler.rescale_from_height(star_asset, star_height)
        star_x = self.note_x_placement[0] - star_asset.get_width() // 4
        star_y = self.note_y_placement[0] + self.staff.line_spacing * 1.5
        perfected_completed_text = f"{self.perfected_chapters}/{self.total_chapters}"
        text = pygame.font.Font(None, size=24).render(perfected_completed_text, True, "black")
        text_y = star_y + star_height + 5
        self.surface.blit(text, (star_x + 5, text_y))
        self.surface.blit(star_asset, (star_x, star_y))

    def __render_second_chord(self):
        for i in range(2):
            self.note_renderer.quarter(
                x_pos=self.note_x_placement[2],
                y_pos=self.note_y_placement[i + 1],
                color=("black" if self.module.chapters[0]["completed"] else "gray"),
            )

    def __render_third_chord(self):
        for i in range(2):
            self.note_renderer.quarter(
                x_pos=self.note_x_placement[6],
                y_pos=self.note_y_placement[i + 2],
                color=("black" if self.module.chapters[2]["completed"] else "gray"),
            )