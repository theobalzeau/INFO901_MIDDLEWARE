from threading import Lock, Thread
from time import sleep
from Communication import Communication

class NodeProcess(Thread):

    def __init__(self, identifier: str, total_processes: int):
        Thread.__init__(self)
        
        self.com_channel = Communication(total_processes)
        self.process_count = self.com_channel.get_process_count()
        self.process_id = self.com_channel.get_process_id()
        self.assign_name(identifier)

        self.is_active = True
        self.start()

    def assign_name(self, identifier: str):
        self.name = identifier

    def execute_critical_action(self):
        """
        Perform the critical section task
        :return: None
        """
        if self.com_channel.message_box.is_empty():
            print("Success! No messages.")
            self.com_channel.broadcast("I won the race!")
        else:
            print(self.com_channel.message_box.getMsg().get_sender(), "acquired the token first.")

    def run(self):
        iteration = 0
        while self.is_active:
            print(f"{self.getName()} Iteration: {iteration}")
            sleep(1)

            if self.getName() == "P0":
                self.com_channel.send_to("Calling P1, will follow up later.", 1)

                self.com_channel.sync_send("I left a message for P1, let's synchronize and get ready to start the game.", 2)
                print("Response from P2: ", self.com_channel.sync_receive(2))

                self.com_channel.sync_send("P2 is ready, let's sync and begin!", 1)

                self.com_channel.synchronize()
                self.com_channel.perform_critical_action(self.execute_critical_action)

            if self.getName() == "P1":
                if not self.com_channel.message_box.is_empty():
                    self.com_channel.message_box.getMsg()
                    print(self.com_channel.sync_receive(0))

                    self.com_channel.synchronize()
                    self.execute_critical_action()

            if self.getName() == "P2":
                print(self.com_channel.sync_receive(0))
                self.com_channel.sync_send("Confirmed", 0)

                self.com_channel.synchronize()
                self.execute_critical_action()

            iteration += 1
        print(f"{self.getName()} has stopped.")

    def stop(self):
        self.is_active = False
        self.join()
