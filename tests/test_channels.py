from . import BaseTests

import goless
import goless.channels as gochans
from goless.backends import current as be
from goless.compat import range


class ChanTests(BaseTests):
    def test_return_types(self):
        self.assertIsInstance(gochans.chan(0), gochans.SyncChannel)
        self.assertIsInstance(gochans.chan(None), gochans.SyncChannel)
        self.assertIsInstance(gochans.chan(-1), gochans.AsyncChannel)
        self.assertIsInstance(gochans.chan(1), gochans.BufferedChannel)


class ChanTestMixin(object):
    def makechan(self):
        raise NotImplementedError()

    def test_send_on_closed_chan_will_raise(self):
        chan = self.makechan()
        chan.close()
        self.assertRaises(gochans.ChannelClosed, lambda: chan < None)

    def test_recv_on_closed_chan_after_chan_empties(self):
        chan = self.makechan()

        be.run(lambda: chan < 'hi')
        self.assertEqual(-chan, 'hi')
        chan.close()
        self.assertRaises(gochans.ChannelClosed, lambda: ~chan)
        self.assertIsNone(-chan)

    def test_range_with_closed_channel(self):
        chan = self.makechan()
        sendCount = min(chan.maxsize, 5)
        data2send = list(range(sendCount))
        for data in data2send:
            be.run(lambda: chan < data)
        chan.close()
        items = [o for o in chan]
        self.assertEqual(items, data2send)

    def test_range_with_open_channel_blocks(self):
        # TODO: Add tests.
        pass

    def _test_channel_raises_when_closed(self, chan_method_name):
        chan = self.makechan()
        method = getattr(chan, chan_method_name)
        marker = []

        def catch_raise():
            try:
                method()
            except gochans.ChannelClosed:
                marker.append(1)
            marker.append(2)

        be.run(catch_raise)
        chan.close()
        be.yield_()
        self.assertEqual(marker, [1, 2])

    def test_channel_recv_raises_when_closed(self):
        self._test_channel_raises_when_closed('recv')

    def test_channel_recvq_returns_none_when_closed(self):
        chan = self.makechan()

        def receive():
            self.assertIsNone(-chan)

        be.run(receive)
        chan.close()
        be.yield_()


class SyncChannelTests(BaseTests, ChanTestMixin):
    def makechan(self):
        return gochans.SyncChannel()

    def test_behavior(self):
        chan = gochans.SyncChannel()
        results = []

        goless.go(lambda: chan < 1)

        def check_results_empty():
            self.assertFalse(results)
            chan < 2
        goless.go(check_results_empty)

        results = [-chan, -chan]
        self.assertEqual(results, [1, 2])

    def test_channel_send_raises_when_closed(self):
        self._test_channel_raises_when_closed('send')

    def _successful_op_does_not_yield_control(self, thisop, otherop):
        chan = self.makechan()
        actions = []

        def other():
            actions.append('other pending')
            getattr(chan, otherop)()
            actions.append('other acted')

        actions.append('other start')
        goless.go(other)
        actions.append('this pending')
        getattr(chan, thisop)()
        actions.append('this acted')

        self.assertEqual(actions, [
            'other start',
            'this pending',
            'other pending',
            'other acted',
            'this acted'
        ])


class AsyncChannelTests(BaseTests, ChanTestMixin):
    def makechan(self):
        return gochans.AsyncChannel()

    def test_behavior(self):
        # Obviously we cannot test an infinite buffer,
        # but we can just test a huge one's behavior.
        chan = gochans.AsyncChannel()
        for _ in range(10000):
            chan < None
        chan.close()
        for _ in chan:
            pass


class BufferedChannelTests(BaseTests, ChanTestMixin):
    def makechan(self):
        return gochans.BufferedChannel(2)

    def test_size_must_be_valid(self):
        for size in '', None:
            self.assertRaises(AssertionError, gochans.BufferedChannel, size)

    def test_recv_and_send_with_room_do_not_block(self):
        resultschan = gochans.BufferedChannel(5)
        endchan = gochans.SyncChannel()

        def square(x):
            return x * x

        def func():
            for num in range(5):
                resultschan < square(num)
            endchan < None

        goless.go(func)
        # Waiting on the endchan tells us our results are
        # queued up in resultschan
        -endchan
        got = [-resultschan for _ in range(5)]
        ideal = [square(i) for i in range(5)]
        self.assertEqual(got, ideal)

    def test_recv_and_send_with_full_buffer_block(self):
        chan = gochans.BufferedChannel(2)
        markers = []

        def sendall():
            markers.append(chan < 4)
            markers.append(chan < 3)
            markers.append(chan < 2)
            markers.append(chan < 1)
        sender = be.run(sendall)
        self.assertEqual(len(markers), 2)
        got = [-chan, -chan]
        be.resume(sender)
        self.assertEqual(len(markers), 4)
        self.assertEqual(got, [4, 3])
        got.extend([-chan, -chan])
        self.assertEqual(got, [4, 3, 2, 1])

    def test_recv_with_no_items_blocks(self):
        chan = gochans.BufferedChannel(1)
        markers = []

        def recvall():
            markers.append(-chan)
            markers.append(-chan)
        be.run(recvall)
        self.assertEqual(markers, [])
        chan < 1
        self.assertEqual(markers, [1])
        chan < 2
        self.assertEqual(markers, [1, 2])


class BackendChannelSenderReceiverPriorityTest(BaseTests):
    """
    Tests if the current backend channel implementation has the correct
    sender/receiver priority (aka preference in stackless).
    Current implementations of goless channels
    depend on receiver having the execution priotity!
    """

    def test_has_correct_sender_receiver_priority(self):
        c = be.channel()
        r = []

        def do_send():
            r.append("s1")
            c.send(None)
            r.append("s2")

        def do_receive():
            r.append("r1")
            c.receive()
            r.append("r2")

        be.run(do_receive)
        be.run(do_send)
        be.yield_()
        self.assertEqual(["r1", "s1", "r2", "s2"], r)

    def test_successful_recv_continues(self):
        """Test that recv with a waiting sender
        *does not* give control to the waiting sender."""
        chan = goless.chan()
        actions = []

        def other():
            actions.append('recv pending')
            -chan
            actions.append('recv acted')

        goless.go(other)
        actions.append('send pending')
        chan < None
        actions.append('send acted')

        self.assertEqual(actions, [
            'send pending',
            'recv pending',
            'recv acted',
            'send acted',
        ])

    def test_successful_recv_does_yield_control(self):
        """Test that send with a waiting receiver
        *does* give control to the waiting receiver."""
        chan = goless.chan()
        actions = []

        def other():
            actions.append('send pending')
            chan < None
            actions.append('send acted')

        goless.go(other)
        actions.append('recv pending')
        -chan
        actions.append('recv acted')

        self.assertEqual(actions, [
            'recv pending',
            'send pending',
            'recv acted',
        ])
