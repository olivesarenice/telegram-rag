from dataclasses import dataclass
from typing import List


@dataclass
class UserConfig:
    username: str
    allowed_chat_id_hash: List[int]


# Example usage
user_config = UserConfig(
    username="meowingcats",
    allowed_chat_id_hash=[
        "a03b85dc0a3680a79c0c0155accaef1d10c605760838c98f35338efa1fcc45e9",
    ],
)
