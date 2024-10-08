
from pathlib import Path
from unittest import TestCase

from ..utils import (
    create_secret_key,
    shortest_path,
)


class TestCreateSecretKey(TestCase):
    def test_create_secret_key(self):
        key = create_secret_key()
        self.assertEqual(len(key), 50)


class TestShortestPath(TestCase):
    def test_down1(self):
        """
        Change 'down' into a subfolder of the cwd directory.
        """
        # Absolute
        cwd = Path('/home/john/')
        target = Path('/home/john/invoices/master.ods')
        self.assertEqual(shortest_path(target, cwd), 'invoices/master.ods')

        # Relative
        cwd = Path('.')
        target = Path('./invoices/master.ods')
        self.assertEqual(shortest_path(target, cwd), 'invoices/master.ods')

    def test_down3(self):
        # Absolute
        cwd = Path('/home/john/invoices/')
        target = Path('/home/john/invoices/2020/04/23/solar.odt')
        self.assertEqual(shortest_path(target, cwd), '2020/04/23/solar.odt')

        # Relative
        cwd = Path('.')
        target = Path('./2020/04/23/solar.odt')
        self.assertEqual(shortest_path(target, cwd), '2020/04/23/solar.odt')

    def test_up1(self):
        # Absolute
        cwd = Path('/home/john/invoices/2020/')
        target = Path('/home/john/invoices/')
        self.assertEqual(shortest_path(target, cwd), '..')

    def test_up3(self):
        cwd = Path('/home/john/invoices/2020/04/23/')
        target = Path('/home/john/invoices/')
        self.assertEqual(shortest_path(target, cwd), '../../..')

    def test_up4(self):
        """
        There should be a limit to the number of '..' parts in a path!
        """
        cwd = Path('/home/john/invoices/2020/04/23/1/')
        target = Path('/home/john/invoices/')
        self.assertEqual(shortest_path(target, cwd), '/home/john/invoices')

    def test_up1_down1(self):
        # Absolute
        cwd = Path('/home/john/invoices/2020/')
        target = Path('/home/john/invoices/master.ods')
        self.assertEqual(shortest_path(target, cwd), '../master.ods')

    def test_up2_down1(self):
        # Absolute
        cwd = Path('/home/john/invoices/2020/04/')
        target = Path('/home/john/invoices/master.ods')
        self.assertEqual(shortest_path(target, cwd), '../../master.ods')

    def test_up3_down3(self):
        # Absolute
        cwd = Path('/home/john/invoices/2020/04/')
        target = Path('/home/john/covers/2019/fiji.png')
        self.assertEqual(shortest_path(target, cwd), '../../../covers/2019/fiji.png')
