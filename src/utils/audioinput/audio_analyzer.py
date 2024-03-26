import copy
from pyaudio import PyAudio, paInt16
from threading import Thread
import numpy as np
import sys


class AudioAnalyzer(Thread):
    SAMPLING_RATE = 48000
    CHUNK_SIZE = 1024
    BUFFER_TIMES = 50
    ZERO_PADDING = 3
    NUM_HPS = 3
    NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

    def __init__(self, queue, *args, **kwargs):
        Thread.__init__(self, *args, **kwargs)

        self.queue = queue  # queue should be instance of ProtectedList (threading_helper.ProtectedList)
        self.buffer = np.zeros(self.CHUNK_SIZE * self.BUFFER_TIMES)
        self.hanning_window = np.hanning(len(self.buffer))
        self.running = False

        try:
            self.audio_object = PyAudio()
            self._list_audio_devices()
            # TODO uncomment the following line and remove the line after that to let the user choose the input device
            # device_index = int(input("Enter the index of the audio input device you want to use: "))
            device_index = 2
            self.stream = self.audio_object.open(format=paInt16,
                                                 channels=1,
                                                 rate=self.SAMPLING_RATE,
                                                 input=True,
                                                 output=False,
                                                 frames_per_buffer=self.CHUNK_SIZE,
                                                 input_device_index=device_index)
        except Exception as e:
            sys.stderr.write('Error: Line {} {} {}\n'.format(sys.exc_info()[-1].tb_lineno, type(e).__name__, e))
            return

    def _list_audio_devices(self):
        """ lists all available audio input devices """
        for i in range(self.audio_object.get_device_count()):
            dev = self.audio_object.get_device_info_by_index(i)
            max_input_channels = dev.get('maxInputChannels')
            host_api_index = self.audio_object.get_default_host_api_info()['index']
            if isinstance(max_input_channels, int) and isinstance(host_api_index, int) and max_input_channels > 0 and dev.get('hostApi') == host_api_index:
                print(i, dev.get('name'))

    @staticmethod
    def frequency_to_number(freq, a4_freq):
        """ converts a frequency to a note number (for example: A4 is 69)"""

        if freq == 0:
            sys.stderr.write("Error: No frequency data. Program has potentially no access to microphone\n")
            return 0

        return 12 * np.log2(freq / a4_freq) + 69

    @staticmethod
    def number_to_frequency(number, a4_freq):
        """ converts a note number (A4 is 69) back to a frequency """

        return a4_freq * 2.0**((number - 69) / 12.0)

    @staticmethod
    def number_to_note_name(number):
        """ converts a note number to a note name (for example: 69 returns 'A', 70 returns 'A#', ... ) """

        return AudioAnalyzer.NOTE_NAMES[int(round(number) % 12)]

    @staticmethod
    def frequency_to_note_name(frequency, a4_freq):
        """ converts frequency to note name (for example: 440 returns 'A') """

        number = AudioAnalyzer.frequency_to_number(frequency, a4_freq)
        note_name = AudioAnalyzer.number_to_note_name(number)
        note_number = number // 12
        return note_name + str(int(note_number))

    def run(self):
        """ Main function where the microphone buffer gets read and
            the fourier transformation gets applied """

        self.running = True

        while self.running:
            try:
                # read microphone data
                data = self.stream.read(self.CHUNK_SIZE, exception_on_overflow=False)
                data = np.frombuffer(data, dtype=np.int16)

                # append data to audio buffer
                self.buffer[:-self.CHUNK_SIZE] = self.buffer[self.CHUNK_SIZE:]
                self.buffer[-self.CHUNK_SIZE:] = data

                # apply the fourier transformation on the whole buffer (with zero-padding + hanning window)
                magnitude_data = abs(np.fft.fft(np.pad(self.buffer * self.hanning_window,
                                                       (0, len(self.buffer) * self.ZERO_PADDING),
                                                       "constant")))
                # only use the first half of the fft output data
                magnitude_data = magnitude_data[:int(len(magnitude_data) / 2)]

                # HPS: multiply data by itself with different scalings (Harmonic Product Spectrum)
                magnitude_data_orig = copy.deepcopy(magnitude_data)
                for i in range(2, self.NUM_HPS+1, 1):
                    hps_len = int(np.ceil(len(magnitude_data) / i))
                    magnitude_data[:hps_len] *= magnitude_data_orig[::i]  # multiply every i element

                # get the corresponding frequency array
                frequencies = np.fft.fftfreq(int((len(magnitude_data) * 2) / 1),
                                             1. / self.SAMPLING_RATE)

                # set magnitude of all frequencies below 60Hz to zero
                for i, freq in enumerate(frequencies):
                    if freq > 60:
                        magnitude_data[:i - 1] = 0
                        break

                # put the frequency of the loudest tone into the queue
                self.queue.put(round(frequencies[np.argmax(magnitude_data)], 2))

            except Exception as e:
                sys.stderr.write('Error: Line {} {} {}\n'.format(sys.exc_info()[-1].tb_lineno, type(e).__name__, e))

        self.stream.stop_stream()
        self.stream.close()
        self.audio_object.terminate()
        
    def stop(self):
        self.running = False

if __name__ == "__main__":
    # Only for testing:
    from audioinput.threading_helper import ProtectedList
    import time

    q = ProtectedList()
    a = AudioAnalyzer(q)
    a.start()

    while True:
        q_data = q.get()
        if q_data is not None:
            print("loudest frequency:", q_data, "nearest note:", a.frequency_to_note_name(q_data, 440))
            time.sleep(0.02)
