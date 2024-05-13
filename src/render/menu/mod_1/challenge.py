import re
import statistics
import time
from random import randint
from typing import List, Literal

import numpy as np
import pygame
import sounddevice as sd
from pygame import Surface
from pygame.event import Event

from src.utils.audioinput.audio_analyzer import AudioAnalyzer
from src.utils.audioinput.threading_helper import ProtectedList
from ....utils.button import Button
from ....utils.challenge_model import ChallengeBase
from ....utils.save_operations.read_save import Save

vol = 0
prev_vol = 0


class Challenge(ChallengeBase):
    def __init__(
            self,
            screen: Surface,
            change_state,
            chapter_index: int,
            use_audio: bool = False,
            num_challenges: int = 10,
            chromatic: bool = False
    ) -> None:
        super().__init__(screen, change_state, chapter_index, use_audio, num_challenges)
        self.staff_notes = ["E", "F", "G", "A", "B", "C", "D", "E", "F"]
        self.__chromatic = chromatic
        self.__current_note = self.__pick_random_note()
        self.__continue = False
        self.__note_buttons: List[Button] = []
        self.__init_note_buttons()
        self.__continue_button = self.init_continue_button(self.click_continue)
        self.__continue_text = ""
        self.__played_notes = []
        if use_audio:
            self.__start_audio_devices()
        self.__level = self.__regular_challenges if not use_audio else self.__audio_challenges
        self.__start_time = 0
        self.__note_played = None
        self.end_button = self.init_end_button(self.__click_end)
        self.__event: callable = (
            self.__handle_event_with_audio
            if use_audio
            else self.__handle_event_without_audio
        )
        self.go_back_button = self.init_back_button(self.__close_threads)

    def render(self):
        if self.current_challenge == self.num_challenges:
            self.final_screen()
            self.end_button.render()
        else:
            self.__level()
            self.go_back_button.render()

    def event_check(self, event_arg: Event | None = None):
        if self.current_challenge == self.num_challenges:
            self.end_button.event_check(event_arg)
        else:
            self.__event(event_arg)
            self.go_back_button.event_check(event_arg)

        if event_arg.type == pygame.QUIT:
            try:
                self.__close_threads()
            except AttributeError:
                pass

    def __handle_event_without_audio(self, event):
        if not self.__continue:
            for button in self.__note_buttons:
                button.event_check(event)
        else:
            self.__continue_button.event_check(event)

    def __handle_event_with_audio(self, event):
        if self.__continue:
            self.__continue_button.event_check(event)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                self.__continue_button.on_click()

    def __regular_challenges(self):
        self.screen.fill("white")
        self.staff.render()

        sharp = self.__get_sharp_or_flat()

        self.note_renderer.quarter(
            x_pos=self.staff.trebble_cleff_asset.get_width() * 2 + 10,
            y_pos=(self.staff.c3_position - self.staff.note_spacing * 2) - (self.__current_note[1] * self.staff.note_spacing),
            has_sharp=sharp
        )

        text = "Qual nota está sendo exibida?"
        width, _ = self.font.size(text)
        self.screen.blit(
            self.font.render(text, True, "black"),
            (
                (self.screen.get_width() // 2) - (width // 2),
                (self.screen.get_height() // 2),
            ),
        )

        if not self.__continue:
            for button in self.__note_buttons:
                button.render()
        else:
            text_width, text_height = self.font.size(self.__continue_text)
            text_x = self.screen.get_width() // 2 - text_width // 2
            text_y = self.__continue_button.pos[1] - text_height - 10
            self.screen.blit(
                self.font.render(self.__continue_text, True, "black"),
                (text_x, text_y),
            )

            self.__continue_button.render()

    def __audio_challenges(self):
        self.screen.fill("white")
        self.staff.render()

        sharp = self.__get_sharp_or_flat()

        self.note_renderer.quarter(
            x_pos=self.staff.trebble_cleff_asset.get_width() * 2 + 10,
            y_pos=(self.staff.c3_position - self.staff.note_spacing * 2) - self.__current_note[1] * self.staff.note_spacing,
            has_sharp=sharp,
        )

        if self.__note_played is None:
            text = "Use seu microfone para tocar a nota sendo exibida"
            width, _ = self.font.size(text)
            self.screen.blit(
                self.font.render(text, True, "black"),
                (
                    (self.screen.get_width() // 2) - (width // 2),
                    (self.screen.get_height() // 2),
                ),
            )
            self.__get_note()
        else:

            width, _ = self.font.size(self.__continue_text)
            self.screen.blit(
                self.font.render(self.__continue_text, True, "black"),
                (
                    (self.screen.get_width() // 2) - (width // 2),
                    ((self.screen.get_height() // 4) * 3),
                ),
            )
            self.__continue_button.render()

    def __get_sharp_or_flat(self):
        sharp: Literal['none', 'sharp', 'flat']
        if self.__current_note[0].find("#") != -1:
            sharp = 'sharp'
        elif self.__current_note[0].find("b") != -1:
            sharp = 'flat'
        else:
            sharp = 'none'
        return sharp

    def click_continue(self):
        self.__current_note = self.__pick_random_note()
        self.__continue = False
        self.current_challenge += 1
        if self.__note_played is not None:
            self.__note_played = None
            self.__played_notes = []

    def __init_note_buttons(self):
        def check_answer(text: str):
            checked_value = self.__current_note[0]
            checked_value = self.__swap_note_if_invalid(checked_value)

            if text == checked_value:
                self.score += 1
                self.__continue_text = "Correto!"
            else:
                self.__continue_text = (
                        "Incorreto! A resposta correta era: " + checked_value
                )
            self.__continue = True

        buttons = []
        notes = ["C", "D", "E", "F", "G", "A", "B"] if not self.__chromatic else ["C", "C#/Db", "D", "D#/Eb", "E", "F", "F#/Gb", "G",
                                                                                  "G#/Ab", "A", "A#/Bb", "B"]

        for index, letter in enumerate(notes):
            button = Button(
                font=self.font,
                text=letter,
                on_click=lambda x=letter: check_answer(x),
                pos=(
                    (self.screen.get_width() // (len(notes) + 1) * (index + 1)) - 25,
                    self.screen.get_height() // 4 * 3,
                ),
                screen=self.screen,
            )
            buttons.append(button)

        self.__note_buttons = buttons

    def click_end(self):
        save = Save.load()
        chapter = save.md1.chapters[self.chapter_index]

        if self.score >= int(self.num_challenges * 0.7):
            chapter["completed"] = True
            if self.score == self.num_challenges:
                chapter["perfected"] = True
            if self.chapter_index + 1 < len(save.md1.chapters):
                next_chapter = save.md1.chapters[self.chapter_index + 1]
                next_chapter["unlocked"] = True
            else:
                save.md2.unlocked = True
        save.md1.chapters[self.chapter_index] = chapter
        save.save()
        from ..main_menu import Menu

        try:
            self.__close_threads()
        except AttributeError:
            pass

        self.change_state(Menu(self.screen, self.change_state))

    def __pick_random_note(self):
        num = randint(0, len(self.staff_notes) - 1)
        if self.__chromatic:
            hassharp = randint(0, 2)
            return_char = ['', 'b', '#']
            return self.staff_notes[num] + return_char[hassharp], num
        else:
            return self.staff_notes[num], num

    def __click_end(self):
        save = Save.load()
        chapter = save.md1.chapters[self.chapter_index]

        if self.score >= int(self.num_challenges * 0.7):
            chapter["completed"] = True
            if self.score == self.num_challenges:
                chapter["perfected"] = True
            if self.chapter_index + 1 < len(save.md1.chapters):
                next_chapter = save.md1.chapters[self.chapter_index + 1]
                next_chapter["unlocked"] = True
            else:
                save.md2.unlocked = True
        save.md1.chapters[self.chapter_index] = chapter
        save.save()

        try:
            self.__close_threads()
        except AttributeError:
            pass

        from ..main_menu import Menu

        self.change_state(Menu(self.screen, self.change_state))

    def __calc_note_position(self, note: str):
        note_name = note[0]
        has_sharp = note.find("#") != -1
        notes = ["E", "F", "G", "A", "B", "C", "D"]
        note_index = notes.index(note_name)
        pos = (
                self.staff.c3_position
                - (self.staff.note_spacing * note_index)
                - (self.staff.note_spacing * 2)
        )
        self.note_renderer.quarter(
            x_pos=self.staff.trebble_cleff_asset.get_width() * 3 + 10,
            y_pos=pos,
            has_sharp='sharp' if has_sharp else 'none',
            color="gray",
        )

    def __get_note(self):
        end_time = time.time()
        global vol

        if self.__note_played is None and vol > 5 and not self.__continue:
            (
                self.__calc_note_position(self.__played_notes[-1])
                if self.__played_notes
                else None
            )
            if self.__start_time == 0:
                self.__start_time = time.time()

            freq = self.__queue.get()
            if freq is not None:
                note = self.__analyzer.frequency_to_note_name(freq, 440)
                note_letter = re.sub(r"\d", "", note)
                self.__played_notes.append(re.sub(r"\d", "", note_letter))
                self.__calc_note_position(note)

            if end_time - self.__start_time > 1 and self.__start_time != 0:
                self.__process_note_played()
        else:
            self.__start_time = 0
            self.__played_notes = []

    def __process_note_played(self):
        self.__note_played = statistics.mode(self.__played_notes)
        self.__continue = True
        checked_value = self.__current_note[0]

        checked_value = self.__swap_note_if_invalid(checked_value)
        note_equivalents: dict[str, str] = {"Cb": "B", "Db": "C#", "Eb": "D#", "Fb": "E", "Gb": "F#", "Ab": "G#", "Bb": "A#"}
        if checked_value in note_equivalents:
            checked_value = note_equivalents[checked_value]

        if self.__note_played == checked_value:
            self.score += 1
            self.__continue_text = "Correto!"
        else:
            self.__continue_text = (
                    "Incorreto! A nota correta era: "
                    + checked_value
                    + ". Você tocou: "
                    + self.__note_played
            )
        self.__played_notes = []

    @staticmethod
    def __swap_note_if_invalid(checked_value):
        if checked_value == 'E#':
            checked_value = 'F'
        elif checked_value == 'B#':
            checked_value = 'C'
        elif checked_value == 'Cb':
            checked_value = 'B'
        elif checked_value == 'Fb':
            checked_value = 'E'
        return checked_value

    @staticmethod
    def __get_volume(indata, frames, time, status):
        volume_norm = np.linalg.norm(indata) * 10
        global prev_vol
        global vol
        prev_vol = vol
        vol = round(volume_norm, 2)

    def __close_threads(self):
        self.__stream.stop()
        self.__stream.close()
        self.__analyzer.stop()
        self.__analyzer.join()

    def __start_audio_devices(self):
        self.__queue = ProtectedList()
        self.__analyzer = AudioAnalyzer(self.__queue)
        self.__analyzer.start()
        self.__stream = sd.InputStream(callback=self.__get_volume)
        self.__stream.start()