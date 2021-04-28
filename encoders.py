from abc import abstractmethod
from typing import Generic, TypeVar
import json

M = TypeVar('M')

class BaseEncoder(Generic[M]):
    @abstractmethod
    def encode(self, message:M) -> bytes:
        raise NotImplementedError(
            'Must implement {}'.format(
                self.__class__.__name__ + '.encode(message:M) -> bytes',
            ),
        )

    @abstractmethod
    def decode(self, data:bytes) -> M:
        raise NotImplementedError(
            'Must implement {}'.format(
                self.__class__.__name__ + '.decode(data:bytes) -> message:M',
            ),
        )

class JsonEncoder(BaseEncoder[dict]):
    def encode(self, message:dict) -> bytes:
        return json.dumps(message, separators=(',', ':')).encode('utf-8')

    def decode(self, data:bytes) -> dict:
        return json.loads(data)

if __name__ == '__main__':
    import unittest

    class JsonEncoderTests(unittest.TestCase):
        def test_encode(self):
            encoder = JsonEncoder()

            self.assertEqual(
                encoder.encode({
                    'dict': {},
                    'int': 42,
                    'str': 'Hello, world',
                }),
                b'{"dict":{},"int":42,"str":"Hello, world"}',
            )

        def test_decode(self):
            encoder = JsonEncoder()

            self.assertEqual(
                encoder.decode(b'{"dict":{},"int":42,"str":"Hello, world"}'),
                {
                    'dict': {},
                    'int': 42,
                    'str': 'Hello, world',
                },
            )

    unittest.main()
