from abc import ABC, abstractmethod


class PaymentProvider(ABC):
    @abstractmethod
    async def create_payment(self, **kwargs): ...


class PaymentService:
    """Provider boundary only; no payment gateway is connected in V1."""

    def __init__(self, provider: PaymentProvider | None = None):
        self.provider = provider
