import pygame
from pygame import Surface
from pygame.event import Event

from src.render.staff import Staff
from src.utils.image_rescaler import ImageRescaler
from src.utils.module_model import ModuleClass
from src.utils.save_operations.read_save import Module, Save


class Module1(ModuleClass):
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
        self.__note_y_placement = [
            self.staff.c3_position - (i * self.staff.line_spacing) for i in range(4)
        ]
        self.__note_x_placements = self.calculate_note_x_placements(width, 9)

        self.first_chord_rect = self.calculate_rect(self.__note_x_placements[0], self.__note_y_placement[2], 3)
        self.text = self.generate_text(module, "Clave e notas")

    def render(self):
        text = pygame.font.Font(None, size=32).render(self.text, True, "black")
        text_x = (self.screen.get_width() - text.get_width()) // 2
        text_y = self.screen.get_height() // 4
        self.screen.blit(text, (text_x, text_y))
        self.__render_chord()
        self.__render_chapters_1_to_3()
        pygame.draw.line(
            self.screen,
            "black",
            (self.__note_x_placements[4], self.staff.line_positions[0]),
            (self.__note_x_placements[4], self.staff.line_positions[-1]),
            5,
        )
        self.__render_chapters_6_to_9()

    def __render_chapters_1_to_3(self):
        for i in range(3):
            self.draw_chapter_quarter((self.__note_x_placements[i + 1], self.__note_y_placement[i]), i)

    def __render_chapters_6_to_9(self):
        for i in range(6, 9):
            self.note_renderer.quarter(self.__note_x_placements[5], self.__note_y_placement[i - 5],
                                       color=("black" if self.module.chapters[2]["completed"] else "gray"),
                                       )

        for i in range(6, 9):
            self.draw_chapter_quarter((self.__note_x_placements[i], self.__note_y_placement[i - 5]), i - 3)

    def event_check(self, event_arg: Event | None = None):
        def check_and_change(x_placement, y_placement, height, chapter_index, use_audio=False, num_challenges=10, chromatic=False,
                             unlock_next=True):
            if (
                    self.calculate_rect(x_placement, y_placement, height).collidepoint(event_arg.pos)
                    and self.module.chapters[chapter_index]["unlocked"]
            ):
                self.action_sound.play()
                from .challenge import Challenge
                self.change_state(
                    Challenge(self.screen, self.change_state, chapter_index, use_audio, num_challenges, chromatic, unlock_next))

        if event_arg.type == pygame.MOUSEBUTTONDOWN:
            if self.first_chord_rect.collidepoint(event_arg.pos):
                from .explanation_1 import Explanation1

                self.change_state(Explanation1(self.screen, self.change_state))

            check_and_change(self.__note_x_placements[1], self.__note_y_placement[0], 1, 0)
            check_and_change(self.__note_x_placements[2], self.__note_y_placement[1], 1, 1, True)
            check_and_change(self.__note_x_placements[3], self.__note_y_placement[2], 1, 2, True, 15, )

            if (
                    self.calculate_rect(self.__note_x_placements[5], self.__note_y_placement[3], 3).collidepoint(event_arg.pos)
                    and self.module.chapters[2]["completed"]
            ):
                save = Save.load()
                chapter = save.md1.chapters[3]
                chapter["unlocked"] = True
                save.md1.chapters[3] = chapter
                save.save()
                from .explanation_2 import Explanation2

                self.change_state(Explanation2(self.screen, self.change_state))

            check_and_change(self.__note_x_placements[6], self.__note_y_placement[1], 1, 3, False, 10, True)
            check_and_change(self.__note_x_placements[7], self.__note_y_placement[2], 1, 4, True, 10, True)
            check_and_change(self.__note_x_placements[8], self.__note_y_placement[3], 1, 5, True, 12, True)

    def __render_chord(self):
        for i in range(3):
            self.note_renderer.quarter(
                x_pos=self.__note_x_placements[0],
                y_pos=self.__note_y_placement[0] - (self.staff.line_spacing * i),
            )
        star_asset = (
            self.blank_star
            if self.perfected_chapters != self.total_chapters
            else self.full_star
        )
        star_height = 30
        star_asset = ImageRescaler.rescale_from_height(star_asset, star_height)
        star_x = self.__note_x_placements[0] - star_asset.get_width() // 4
        star_y = self.first_chord_rect.bottom + self.staff.line_spacing
        perfected_completed_text = f"{self.perfected_chapters}/{self.total_chapters}"
        text = pygame.font.Font(None, size=24).render(perfected_completed_text, True, "black")
        text_y = star_y + star_height + 5
        self.screen.blit(text, (star_x + 5, text_y))
        self.screen.blit(star_asset, (star_x, star_y))
