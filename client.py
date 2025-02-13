import json
import asyncio
import curses
import random
from functools import partial

import websockets

# Константы
MAP_WIDTH = 20
MAP_HEIGHT = 20
TICK_RATE = 0.03  # 30ms

MOVES = {
    119: 2,
    100: 1,
    115: 0,
    97: 3,
}


class ClientEngine:
    def __init__(self, stdscr, websocket_uri):
        self._all_players = []
        self.websocket_uri = websocket_uri

        self.stdscr = stdscr
        self.running = True
        self.player_x = 1
        self.player_y = MAP_HEIGHT - 2
        # self.score = 0
        # self.snowflakes = set()
        # self.current_keys = set()

        # Настройка curses
        curses.curs_set(0)
        self.stdscr.nodelay(True)
        self.stdscr.timeout(30)  # 30ms

        # self.generate_snowflakes(1)  # Начальные цели

    def apply_server_updates_for_all_players(self, all_players):
        self.player_x, self.player_y = all_players[0]
        self._other_players = all_players[1:]
        self.draw()

    # def generate_snowflakes(self, count=1):
    #     """Генерирует `count` объектов (*) в случайных местах карты."""
    #     for _ in range(count):
    #         while True:
    #             x, y = random.randint(1, MAP_WIDTH - 2), random.randint(1, MAP_HEIGHT - 2)
    #             if (y, x) not in self.snowflakes and (y, x) != (self.player_y, self.player_x):
    #                 self.snowflakes.add((y, x))
    #                 break

    def draw(self):
        """Отрисовка карты в консоли."""
        self.stdscr.clear()

        # Границы
        self.stdscr.addstr(0, 0, "+" + "-" * (MAP_WIDTH - 2) + "+")
        for y in range(1, MAP_HEIGHT - 1):
            self.stdscr.addstr(y, 0, "|")
            self.stdscr.addstr(y, MAP_WIDTH - 1, "|")
        self.stdscr.addstr(MAP_HEIGHT - 1, 0, "+" + "-" * (MAP_WIDTH - 2) + "+")

        # Объекты
        # for y, x in self.snowflakes:
        #     self.stdscr.addch(y, x, "*")

        # other players
        for player_coordinates in self._other_players:
            self.stdscr.addch(player_coordinates[1], player_coordinates[0], "o")

        # Игрок
        self.stdscr.addch(self.player_y, self.player_x, "0")

        # Счет
        # self.stdscr.addstr(MAP_HEIGHT, 0, f"Score: {self.score}")

        self.stdscr.refresh()

    async def input_handler(self):
        """Асинхронно обрабатывает ввод с клавиатуры."""
        while self.running:

            key = self.stdscr.getch()
            if key != -1:
                try:
                    await self.send_move_to_server(MOVES[key])
                except KeyError:
                    if key == ord("q"):
                        self.running = False
            await asyncio.sleep(TICK_RATE)

    async def run(self):
        """Запускает игру."""
        async with websockets.connect(self.websocket_uri) as websocket:
            self.websocket = websocket
            await asyncio.gather(
                self.input_handler(),
                self.receive_messages_from_server(),
            )

    async def send_move_to_server(self, key):
        await self._send_message_to_server(json.dumps(key))

    async def _send_message_to_server(self, message):
        """Отправляет сообщение на сервер"""
        # print(f"Sending: {message}")
        await self.websocket.send(message)

    async def receive_messages_from_server(self):
        """Получает и обра��атывает сообщения от сервера"""
        while True:
            try:
                message = await self.websocket.recv()
                self.apply_server_updates_for_all_players(json.loads(message))
            except websockets.exceptions.ConnectionClosed:
                break


if __name__ == "__main__":
    ClientEngine = partial(ClientEngine, websocket_uri="ws://localhost:8000/ws")
    client_engine = curses.wrapper(ClientEngine)
    asyncio.run(client_engine.run())
