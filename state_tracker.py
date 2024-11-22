class StateTracker:
    def __init__(self, ga_logger, telegraf_logger):
        self.current_page = None
        self.attributes = {}
        self.ga_logger = ga_logger
        self.telegraf_logger = telegraf_logger
        self.cart = []  # Track items added to the cart

    def set_page(self, page_name, **attributes):
        """
        Sets the current page and its attributes and logs the change.
        """

        # Log the state to Google Analytics
        if page_name != self.current_page:
            self.ga_logger.log_page_view(
                page_title=page_name,
                page_location=f"https://app.washterminalpro.nl/{page_name.lower().replace(' ', '-')}",
                **attributes
            )

        self.current_page = page_name
        self.attributes = attributes

        # Special handling for specific pages
        if page_name.startswith("program_selection"):
            self.ga_logger.start_new_session()
            self.ga_logger.track_view_item_list(
                item_list_name="Programs",
                items=attributes.get("items", [])
            )

        if page_name == "payment":
            self.add_payment_info("pin")

        if page_name == "payment_washcard":
            self.add_payment_info("washcard")

        # Log the state to Telegraf
        tags = {"page": page_name}
        fields = {k: v for k, v in attributes.items() if isinstance(v, (int, float))}
        self.telegraf_logger.log_metrics("state_tracker", tags, fields)

    def add_to_cart(self, item):
        """
        Adds an item to the cart and logs the 'add_to_cart' event.
        :param item: A dictionary with item details.
        """
        self.cart.append(item)
        self.ga_logger.track_add_to_cart(item)

    def add_payment_info(self, payment_method):
        """
        Logs the 'add_payment_info' event.
        :param payment_method: The payment method used (e.g., 'pin', 'cashcard').
        """
        self.ga_logger.track_add_payment_info(payment_method)

    def purchase(self, transaction_id):
        """
        Logs the 'purchase' event and clears the cart.
        :param transaction_id: Unique transaction ID for the purchase.
        """
        total_value = sum(item.get("price", 0) for item in self.cart)
        self.ga_logger.track_purchase(
            transaction_id=transaction_id,
            items=self.cart,
            total_value=total_value
        )
        self.cart.clear()

    def get_page(self):
        return self.current_page

    def get_attribute(self, key, default=None):
        return self.attributes.get(key, default)

    def clear(self):
        self.current_page = None
        self.attributes = {}
        self.ga_logger.start_new_session()
