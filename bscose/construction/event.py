from typing import Callable, TypeVar

SomeTypeOfEvent = TypeVar("SomeTypeOfEvent", bound='Event', contravariant=True)

class Event:
    def __init__(self, event_description: str = None) -> None:
        self._description = event_description if event_description is not None else ""

    @property
    def description(self) -> str:
        return self._description

class Announcer:
    def __init__(self) -> None:
        self._subscription_mapping: dict[str, Callable[[Event], None]] = {}
        self._topic_mapping : dict[type[Event], set[str]] = {}
        self._reverse_topic_mapping : dict[str, type[Event]] = {}

    def add_subscription(self, event_type: type[SomeTypeOfEvent], subscriber_action: Callable[[SomeTypeOfEvent], None]) -> str:
        if event_type not in self._topic_mapping:
            self._topic_mapping[event_type] = set()
        new_id = self._generate_new_id(event_type, subscriber_action)
        self._subscription_mapping[new_id] = subscriber_action
        self._topic_mapping[event_type].add(new_id)
        return new_id

    def remove_subscription(self, subscriber_id: str, return_if_not_found: bool = False) -> bool:
        if subscriber_id not in self._subscription_mapping:
            if return_if_not_found:
                return False
            raise ValueError(f"Subscription id {subscriber_id} not found.")
        self._topic_mapping[self._reverse_topic_mapping[subscriber_id]].discard(subscriber_id)
        del self._reverse_topic_mapping[subscriber_id]
        del self._subscription_mapping[subscriber_id]
        return True

    def announce_event(self, event: SomeTypeOfEvent) -> int:
        if type(event) not in self._topic_mapping:
            return 0
        subscriber_set = self._topic_mapping[type(event)]
        for subscriber_id in subscriber_set:
            self._subscription_mapping[subscriber_id](event) # call the subscriber method
        return len(subscriber_set)

    def _generate_new_id(self, event_type: type[SomeTypeOfEvent], subscriber_action: Callable[[SomeTypeOfEvent], None]) -> str:
        return f"{id(self)}-{event_type.__name__}-{id(subscriber_action)}"
