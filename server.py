import uuid
from typing import Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

FIELD_SIZE = 20


def get_uuid() -> str:
    return str(uuid.uuid4())


class ConnectionManager:
    def __init__(self):
        self.active_players: Dict[str, Dict] = {}

    async def connect(self, websocket: WebSocket, _id: str):
        """Добавляет нового клиента в список"""
        await websocket.accept()
        self.active_players[_id] = {
            'websocket': websocket,
            'position': (0, 0),
        }

    async def disconnect(self, _id: str):
        """Удаляет клиента из списка при отключении"""
        del self.active_players[_id]

    async def broadcast_players_positions(self):
        """Отправляет сообщение всем подключённым клиентам"""
        for user_id, user_data in self.active_players.items():
            positions = [user_data['position']]
            positions += [
                other_user_data['position']
                for other_user_id, other_user_data in self.active_players.items()
                if other_user_id != user_id
            ]
            print(positions)
            await user_data['websocket'].send_json(positions)

    def calculate_position(self, prev_position, move):
        def normalize_position(position):
            x, y = position
            return max(0, min(FIELD_SIZE, x)), max(0, min(FIELD_SIZE, y))

        if move == 0:
            position = prev_position[0], prev_position[1] + 1
        elif move == 1:
            position = prev_position[0] + 1, prev_position[1]
        elif move == 2:
            position = prev_position[0], prev_position[1] - 1
        elif move == 3:
            position = prev_position[0] - 1, prev_position[1]

        return normalize_position(position)

    async def update_player_position(self, _id: str, move):
        try:
            self.active_players[_id]['position'] = self.calculate_position(
                prev_position=self.active_players[_id]['position'],
                move=move,
            )
        except KeyError:
            pass

        await self.broadcast_players_positions()


def calculate_new_position(key_code, current_position=0):
    return current_position + key_code


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    client_id = get_uuid()
    await manager.connect(websocket, client_id)
    await manager.broadcast_players_positions()

    try:
        while True:
            data = await websocket.receive_json()
            await manager.update_player_position(client_id, int(data))
            print(f"Received data: {data} from {client_id}")
    except WebSocketDisconnect:
        print(f'disconnected {client_id}')
        await manager.disconnect(client_id)
        await manager.broadcast_players_positions()
