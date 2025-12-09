import logging
from typing import List, Optional
from datetime import datetime

# 既存コードのコメント「アプリケーション全体に「app.models」という単一の窓口を提供する。」を考慮し、
# チャット関連のモデルをインポートすることを想定します。
# これらのモデルは、データベースとのやり取りを抽象化する役割を担います。
# 例: from app.models import ChatRoom, ChatMessage, User
# 実際のモデル名と構造に合わせて適宜修正してください。
# ここでは仮のクラスとして定義し、サービス層のロジックを示します。
class ChatRoom:
    def __init__(self, id: Optional[int], name: str, creator_id: int, created_at: datetime, updated_at: datetime):
        self.id = id
        self.name = name
        self.creator_id = creator_id
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    async def get_by_id(cls, room_id: int) -> Optional['ChatRoom']:
        # データベースからチャットルームを取得するロジックをここに実装
        # 例: return await db.fetch_one("SELECT * FROM chat_rooms WHERE id = :id", {"id": room_id})
        # ここではモックデータを返します
        if room_id == 1:
            return ChatRoom(id=1, name="General Chat", creator_id=101, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        return None

    @classmethod
    async def get_by_participant_id(cls, user_id: int) -> List['ChatRoom']:
        # ユーザーが参加しているチャットルームを取得するロジックをここに実装
        # 例: return await db.fetch_all("SELECT cr.* FROM chat_rooms cr JOIN room_participants rp ON cr.id = rp.room_id WHERE rp.user_id = :user_id", {"user_id": user_id})
        # ここではモックデータを返します
        if user_id == 101:
            return [ChatRoom(id=1, name="General Chat", creator_id=101, created_at=datetime.utcnow(), updated_at=datetime.utcnow())]
        return []

    async def save(self):
        # データベースにチャットルームを保存（新規作成または更新）するロジックをここに実装
        pass

class ChatMessage:
    def __init__(self, id: Optional[int], room_id: int, sender_id: int, content: str, sent_at: datetime):
        self.id = id
        self.room_id = room_id
        self.sender_id = sender_id
        self.content = content
        self.sent_at = sent_at

    @classmethod
    async def get_by_room_id(cls, room_id: int, limit: int = 100, offset: int = 0) -> List['ChatMessage']:
        # データベースから指定されたルームのメッセージを取得するロジックをここに実装
        # 例: return await db.fetch_all("SELECT * FROM chat_messages WHERE room_id = :room_id ORDER BY sent_at DESC LIMIT :limit OFFSET :offset", {"room_id": room_id, "limit": limit, "offset": offset})
        # ここではモックデータを返します
        if room_id == 1:
            return [
                ChatMessage(id=1, room_id=1, sender_id=101, content="Hello everyone!", sent_at=datetime.utcnow()),
                ChatMessage(id=2, room_id=1, sender_id=102, content="Hi there!", sent_at=datetime.utcnow()),
            ]
        return []

    async def save(self):
        # データベースにメッセージを保存するロジックをここに実装
        pass

# ユーザーモデルも必要に応じてインポートまたは定義
class User:
    def __init__(self, id: int, username: str):
        self.id = id
        self.username = username

    @classmethod
    async def get_by_id(cls, user_id: int) -> Optional['User']:
        # データベースからユーザーを取得するロジックをここに実装
        if user_id == 101:
            return User(id=101, username="user1")
        if user_id == 102:
            return User(id=102, username="user2")
        return None


# ★ ロガーの取得 (既存コードから流用)
logger = logging.getLogger(__name__)

# ====================================================================
# 2. サービス層の実装 - チャット機能
# ====================================================================

class ChatService:
    """
    チャット関連のビジネスロジックを処理するサービス層。
    モデル層（app.models）と連携し、チャットルームの管理、メッセージの送受信、
    履歴の取得などの機能を提供します。
    """

    async def create_chat_room(self, name: str, creator_user_id: int, participants_user_ids: List[int]) -> ChatRoom:
        """
        新しいチャットルームを作成します。

        Args:
            name (str): チャットルームの名前。
            creator_user_id (int): ルームを作成するユーザーのID。
            participants_user_ids (List[int]): 参加者となるユーザーのIDリスト。

        Returns:
            ChatRoom: 作成されたチャットルームオブジェクト。

        Raises:
            ValueError: 参加者ユーザーが見つからない場合。
        """
        logger.info(f"Attempting to create chat room: '{name}' by user {creator_user_id}")

        # 作成者ユーザーの存在確認
        creator = await User.get_by_id(creator_user_id)
        if not creator:
            logger.warning(f"Creator user with ID {creator_user_id} not found.")
            raise ValueError(f"Creator user with ID {creator_user_id} not found.")

        # 参加者ユーザーの存在確認 (オプション、必要に応じて実装)
        # for user_id in participants_user_ids:
        #     if not await User.get_by_id(user_id):
        #         logger.warning(f"Participant user with ID {user_id} not found.")
        #         raise ValueError(f"Participant user with ID {user_id} not found.")

        new_room = ChatRoom(
            id=None, # データベースがIDを生成することを想定
            name=name,
            creator_id=creator_user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        await new_room.save() # データベースに保存

        # 参加者をチャットルームに追加するロジック (Many-to-Many関係の場合)
        # 例: await new_room.add_participants(participants_user_ids)
        # ここでは、作成者も参加者リストに含めるか、別途追加するロジックが必要です。
        # 簡単のため、ここでは省略します。

        logger.info(f"Chat room '{name}' created successfully with ID: {new_room.id}")
        return new_room

    async def get_chat_room(self, room_id: int) -> Optional[ChatRoom]:
        """
        指定されたIDのチャットルームを取得します。

        Args:
            room_id (int): 取得するチャットルームのID。

        Returns:
            Optional[ChatRoom]: 見つかった場合はChatRoomオブジェクト、見つからない場合はNone。
        """
        logger.info(f"Attempting to retrieve chat room with ID: {room_id}")
        room = await ChatRoom.get_by_id(room_id)
        if room:
            logger.debug(f"Chat room {room_id} found: {room.name}")
        else:
            logger.warning(f"Chat room with ID {room_id} not found.")
        return room

    async def send_message(self, room_id: int, sender_user_id: int, content: str) -> ChatMessage:
        """
        指定されたチャットルームにメッセージを送信します。

        Args:
            room_id (int): メッセージを送信するチャットルームのID。
            sender_user_id (int): メッセージの送信者ユーザーのID。
            content (str): メッセージの内容。

        Returns:
            ChatMessage: 送信されたメッセージオブジェクト。

        Raises:
            ValueError: チャットルームまたは送信者ユーザーが見つからない場合。
        """
        logger.info(f"User {sender_user_id} sending message to room {room_id}")

        # チャットルームの存在確認
        room = await self.get_chat_room(room_id)
        if not room:
            raise ValueError(f"Chat room with ID {room_id} does not exist.")

        # 送信者ユーザーの存在確認
        sender = await User.get_by_id(sender_user_id)
        if not sender:
            logger.warning(f"Sender user with ID {sender_user_id} not found.")
            raise ValueError(f"Sender user with ID {sender_user_id} not found.")

        new_message = ChatMessage(
            id=None, # データベースがIDを生成することを想定
            room_id=room_id,
            sender_id=sender_user_id,
            content=content,
            sent_at=datetime.utcnow()
        )
        await new_message.save() # データベースに保存

        logger.info(f"Message sent to room {room_id} by user {sender_user_id}. Message ID: {new_message.id}")
        return new_message

    async def get_messages_in_room(self, room_id: int, limit: int = 100, offset: int = 0) -> List[ChatMessage]:
        """
        指定されたチャットルームのメッセージ履歴を取得します。

        Args:
            room_id (int): メッセージを取得するチャットルームのID。
            limit (int): 取得するメッセージの最大数。
            offset (int): 取得を開始するオフセット。

        Returns:
            List[ChatMessage]: メッセージオブジェクトのリスト。

        Raises:
            ValueError: チャットルームが見つからない場合。
        """
        logger.info(f"Retrieving messages for room {room_id} (limit={limit}, offset={offset})")

        # チャットルームの存在確認
        room = await self.get_chat_room(room_id)
        if not room:
            raise ValueError(f"Chat room with ID {room_id} does not exist.")

        messages = await ChatMessage.get_by_room_id(room_id, limit=limit, offset=offset)
        logger.debug(f"Found {len(messages)} messages for room {room_id}.")
        return messages

    async def get_user_chat_rooms(self, user_id: int) -> List[ChatRoom]:
        """
        指定されたユーザーが参加しているチャットルームのリストを取得します。

        Args:
            user_id (int): チャットルームを取得するユーザーのID。

        Returns:
            List[ChatRoom]: ユーザーが参加しているチャットルームのリスト。
        """
        logger.info(f"Retrieving chat rooms for user {user_id}")
        # ユーザーが参加しているチャットルームを取得するロジックを想定
        rooms = await ChatRoom.get_by_participant_id(user_id)
        logger.debug(f"User {user_id} is a participant in {len(rooms)} chat rooms.")
        return rooms