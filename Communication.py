import random
from time import sleep
from typing import Callable, List

from MessageBox import MessageBox
from pyeventbus3.pyeventbus3 import PyBus, subscribe, Mode
from Message import *

class Communication:

    def __init__(self, process_count: int):
        self.process_count = process_count
        self.process_id = None
        self.initial_ids = []

        self.active_processes = []
        self.potentially_active_processes = []

        PyBus.Instance().register(self, self)
        sleep(1)

        self.message_box = MessageBox()
        self.logical_clock = 0

        self.sync_count = 0
        self.in_sync = False

        self.token_status = TokenState.Null
        self.current_token = None

        self.is_locked = False
        self.waiting_from = []
        self.received_obj = None

        self.is_running = True
        if self.get_process_id() == self.process_count - 1:
            self.current_token = random.randint(0, 10000 * (self.process_count - 1))
            self.dispatch_token()

    def get_process_count(self) -> int:
        return self.process_count

    def get_process_id(self) -> int:
        if self.process_id is None:
            self.initialize_process_id()
        return self.process_id

    def initialize_process_id(self):
        random_value = random.randint(0, 10000 * (self.process_count - 1))
        print(self, ["Generated random id:", random_value])
        self.transmit_message(InitIdMessage(random_value))
        sleep(2)
        if len(set(self.initial_ids)) != self.process_count:
            print("ID conflict, retrying initialization")
            self.initial_ids = []
            return self.initialize_process_id()
        self.initial_ids.sort()
        self.process_id = self.initial_ids.index(random_value)
        print("Assigned process id:", self.process_id, "IDs:", self.initial_ids, "Random value:", random_value)

    @subscribe(threadMode=Mode.PARALLEL, onEvent=InitIdMessage)
    def handle_init_id_message(self, message: InitIdMessage):
        print("Received initialization message with random id:", message.get_object())
        self.initial_ids.append(message.get_object())

    def transmit_message(self, message: Message):
        if not message.is_system:
            self.increment_clock()
            message.horloge = self.logical_clock
        print(message)
        PyBus.Instance().post(message)

    def send_to(self, obj: any, target_process: int):
        self.transmit_message(MessageTo(obj, self.get_process_id(), target_process))

    @subscribe(threadMode=Mode.PARALLEL, onEvent=MessageTo)
    def handle_message(self, message: MessageTo):
        if message.to_id != self.get_process_id() or type(message) in [MessageToSync, Token, AcknowledgementMessage]:
            return
        if not message.is_system:
            self.logical_clock = max(self.logical_clock, message.horloge) + 1
        print("Received Message from", message.from_id, ":", message.get_object())
        self.message_box.store_message(message)

    def sync_send(self, obj: any, target_process: int):
        self.waiting_from = target_process
        self.transmit_message(MessageToSync(obj, self.get_process_id(), target_process))
        while target_process == self.waiting_from:
            if not self.is_running:
                return

    def sync_receive(self, source_process: int) -> any:
        self.waiting_from = source_process
        while source_process == self.waiting_from:
            if not self.is_running:
                return
        result = self.received_obj
        self.received_obj = None
        return result

    @subscribe(threadMode=Mode.PARALLEL, onEvent=MessageToSync)
    def handle_sync_message(self, message: MessageToSync):
        if message.to_id != self.get_process_id():
            return
        if not message.is_system:
            self.logical_clock = max(self.logical_clock, message.horloge) + 1
        while message.from_id != self.waiting_from:
            if not self.is_running:
                return
        self.waiting_from = -1
        self.received_obj = message.get_object()
        self.transmit_message(AcknowledgementMessage(self.get_process_id(), message.from_id))

    def broadcast_sync(self, source_process: int, obj: any = None) -> any:
        if self.get_process_id() == source_process:
            print("Broadcasting synchronously", obj)
            for i in range(self.process_count):
                if i != self.get_process_id():
                    self.sync_send(obj, i)
        else:
            return self.sync_receive(source_process)

    @subscribe(threadMode=Mode.PARALLEL, onEvent=AcknowledgementMessage)
    def handle_acknowledgement(self, event: AcknowledgementMessage):
        if self.get_process_id() == event.to_id:
            print("Acknowledgement received from", event.from_id)
            self.waiting_from = -1

    def synchronize(self):
        self.in_sync = True
        print("Initiating synchronization")
        while self.in_sync:
            sleep(0.1)
            print("Synchronizing...")
            if not self.is_running:
                return
        while self.sync_count != 0:
            sleep(0.1)
            print("Finishing synchronization")
            if not self.is_running:
                return
        print("Synchronization complete")

    def request_critical_section(self):
        print("Requesting access to critical section")
        self.token_status = TokenState.Requested
        while self.token_status == TokenState.Requested:
            if not self.is_running:
                return
        print("Entered critical section")

    def broadcast(self, obj: any):
        self.transmit_message(BroadcastMessage(obj, self.get_process_id()))

    @subscribe(threadMode=Mode.PARALLEL, onEvent=BroadcastMessage)
    def handle_broadcast(self, message: BroadcastMessage):
        if message.from_id == self.get_process_id():
            return
        print("Received broadcast message from", message.from_id, ":", message.get_object())
        if not message.is_system:
            self.logical_clock = max(self.logical_clock, message.horloge) + 1
        self.message_box.store_message(message)

    def dispatch_token(self):
        if self.current_token is None:
            return
        sleep(0.1)
        self.transmit_message(Token(self.get_process_id(), (self.get_process_id() + 1) % self.process_count, self.sync_count, self.current_token))
        self.current_token = None

    def release_critical_section(self):
        print("Releasing critical section")
        if self.token_status == TokenState.SC:
            self.token_status = TokenState.Release
        self.dispatch_token()
        self.token_status = TokenState.Null
        print("Critical section released")

    def increment_clock(self):
        self.logical_clock += 1

    def get_clock(self) -> int:
        return self.logical_clock

    def terminate(self):
        self.is_running = False

    @subscribe(threadMode=Mode.PARALLEL, onEvent=Token)
    def handle_token(self, event: Token):
        if event.to_id != self.get_process_id() or not self.is_running:
            return
        print("Token received from", event.from_id)
        self.current_token = event.currentTokenId
        self.sync_count = event.nbSync + int(self.in_sync) % self.process_count
        self.in_sync = False
        if self.token_status == TokenState.Requested:
            self.token_status = TokenState.SC
        else:
            self.dispatch_token()

    def perform_critical_action(self, function_to_call: Callable, *args: List[any]) -> any:
        self.request_critical_section()
        result = None
        if self.is_running:
            if args is None:
                result = function_to_call()
            else:
                result = function_to_call(*args)
            self.release_critical_section()
        return result
