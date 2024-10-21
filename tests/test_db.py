import asyncio
import unittest
import aiosqlite

from src.db import (
    add_element,
    setup,
    remove_channel,
    channel_exists,
    get_channels,
    get_servers,
    remove_server,
    DATABASE
)

class TestDatabase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Initial database setup for tests
        cls.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(cls.loop)
        cls.loop.run_until_complete(setup())
    
    @classmethod
    def tearDownClass(cls):
        # Cleanup after tests
        async def cleanup():
            async with aiosqlite.connect(DATABASE) as conn:
                await conn.execute("DROP TABLE IF EXISTS servers")
                await conn.execute("DROP TABLE IF EXISTS categories")
                await conn.commit()
        
        cls.loop.run_until_complete(cleanup())

    def test_add_element(self):
        server_id = 123456
        category_type = 'forum'
        item_id = 1
        
        # Add an element
        result = self.loop.run_until_complete(add_element(server_id, category_type, item_id))
        self.assertTrue(result)  # Check that the element was added

        # Try to add the same element again
        result = self.loop.run_until_complete(add_element(server_id, category_type, item_id))
        self.assertFalse(result)  # Check that the element was not added twice

    def test_remove_channel(self):
        server_id = 123456
        category_type = 'forum'
        item_id = 2

        # Add an channel
        self.loop.run_until_complete(add_element(server_id, category_type, item_id))
        self.assertTrue(self.loop.run_until_complete(channel_exists(server_id, item_id)))
        
        # Remove the channel
        self.loop.run_until_complete(remove_channel(server_id, item_id))
        self.assertFalse(self.loop.run_until_complete(channel_exists(server_id, item_id)))

    def test_channel_exists(self):
        server_id = 123456
        category_type = 'forum'
        item_id = 3

        # Check that the channel does not exist before adding
        self.assertFalse(self.loop.run_until_complete(channel_exists(server_id, item_id)))

        # Add an element
        self.loop.run_until_complete(add_element(server_id, category_type, item_id))
        self.assertTrue(self.loop.run_until_complete(channel_exists(server_id, item_id)))

    def test_get_channels(self):
        server_id = 123456
        category_type1 = 'forum'
        item_id1 = 4
        category_type2 = 'post'
        item_id2 = 5

        # Add elements
        self.loop.run_until_complete(add_element(server_id, category_type1, item_id1))
        self.loop.run_until_complete(add_element(server_id, category_type2, item_id2))

        # Retrieve channels
        channels = self.loop.run_until_complete(get_channels(server_id))

        # Check that the channels are retrieved correctly
        self.assertIn('forum', channels)
        self.assertIn('post', channels)
        self.assertIn(item_id1, channels['forum'])
        self.assertIn(item_id2, channels['post'])

    def test_remove_server(self):
        server_id = 123456
        # Add the server to the database
        self.loop.run_until_complete(add_element(server_id, 'dummy', 0))
        servers = self.loop.run_until_complete(get_servers())
        self.assertIn(server_id, servers)

        # Remove the server
        self.loop.run_until_complete(remove_server(server_id))
        servers = self.loop.run_until_complete(get_servers())
        self.assertNotIn(server_id, servers)