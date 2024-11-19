import logging
from kivy.clock import Clock
from kivy.uix.screenmanager import Screen
from kivy.app import App
from payNL import PayNL
from washcard import Washcard


class Payment(Screen):
    transaction_status = ""
    pay = None
    transaction_id = 0
    settings = {}

    def on_enter(self, _, __):
        logging.debug("=== Payment ===")
        app = App.get_running_app()
        self.settings = app.SETTINGS

        # Initialize PayNL and start transaction
        self.pay = PayNL(self.settings["paynl"])
        self.transaction_id = self.pay.payOrder(app.activeOrder)
        app.activeOrder.transaction_id = self.transaction_id
        logging.debug("transaction_id: %s", self.transaction_id)

        # Start polling for transaction status
        self.transaction_status = "PENDING"
        self.elapsed_time = 0  # Track elapsed time
        self.cancel_transaction = False

        # Track transaction id in tracker
        app.tracker.set_page(
            app.sm.current,
            transaction_id=self.transaction_id,
            transaction_status=self.transaction_status,
        )

        # Schedule transaction polling every 0.1 seconds
        Clock.schedule_interval(self.poll_transaction_status, 2)

    def poll_transaction_status(self, dt):
        app = App.get_running_app()
        self.elapsed_time += dt  # Increment elapsed time by 2 seconds

        self.transaction_status = self.pay.get_transaction_status(self.transaction_id)

        # Update tracker
        app.tracker.set_page(
            app.sm.current,
            transaction_id=self.transaction_id,
            transaction_status=self.transaction_status,
        )
        logging.debug("transaction_status: %s", self.transaction_status)

        # Stop polling if the transaction is complete, cancelled, or timed out
        if (
            self.transaction_status != "PENDING"
            or self.elapsed_time >= 40  # 40 seconds timeout
            or self.cancel_transaction
        ):
            Clock.unschedule(self.poll_transaction_status)
            self.handle_transaction_result()

    def handle_transaction_result(self):
        app = App.get_running_app()

        if self.transaction_status == "PAID":
            logging.debug("Payment successful!")
            washcard = Washcard(self.settings)
            response = washcard.pay(app.activeOrder)
            logging.debug(response)
            app.change_screen("payment_success")
        elif self.cancel_transaction:
            logging.debug("Transaction cancelled")
            app.tracker.set_page(
                app.sm.current,
                transaction_id=self.transaction_id,
                transaction_status="CANCELLED",
            )
            self.pay.cancel_transaction()
            app.show_start_screen()
        else:
            logging.debug("Payment error occurred")
            app.tracker.set_page(
                app.sm.current,
                transaction_id=self.transaction_id,
                transaction_status="ERROR",
            )
            Clock.schedule_once(lambda dt: app.change_screen("payment_failed"))

    def cancel(self, _, __):
        logging.debug("=== Cancelling PIN payment ===")
        self.cancel_transaction = True
