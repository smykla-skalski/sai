"""Narration, one clip per beat: {scene class: [(clip key, spoken text), ...]}.

Keys are used in video.py. The text is only spoken, never shown, so it is written
for the ear. Acronyms are hyphenated so the voice reads them letter by letter:
"T-C-P", "U-D-P", "H-T-T-P three", "A-P-I", "Web-R-T-C". QUIC is written "Quick" so
the voice says the word, not the letters; HEARD maps Whisper's spelling back for
transcribe.py.

Copyright 2026 Smykla Skalski, MIT License.
"""

from typing import Final

HEARD: Final = {"quic": "quick"}

BEATS: Final = {
    "Hook": [
        (
            "hook_1",
            (
                "You are playing a game in your browser. Sixty times a second, the "
                "server sends where every other player is. Then, on a busy Wi-Fi "
                "network, one packet gets lost, and the whole world freezes, then "
                "jumps."
            ),
        ),
        (
            "hook_2",
            (
                "One lost packet should cost one small update, not a frozen screen. A "
                "newer web A-P-I, called WebTransport, fixes this. To see how, start "
                "with the tool that browser games use today."
            ),
        ),
    ],
    "Pipe": [
        (
            "pipe_1",
            (
                "That tool is the WebSocket. It starts as an ordinary web request, "
                "then upgrades into one long-lived T-C-P connection, a single pipe "
                "between your browser and the server."
            ),
        ),
        (
            "pipe_2",
            (
                "T-C-P makes a promise. Every byte arrives, and in the order it was "
                "sent. So when packet three is lost, packets four, five and six still "
                "arrive, but the browser cannot hand them to the page. They wait in a "
                "buffer."
            ),
        ),
        (
            "pipe_3",
            (
                "Only when the server notices the loss and sends packet three again, "
                "about one round trip later, does everything come out at once. This is "
                "called head-of-line blocking."
            ),
        ),
        (
            "pipe_4",
            (
                "For a game, that is the worst trade. Positions three to six are "
                "already old when they come out, and only the newest one matters. And "
                "chat messages and downloads share the same pipe, so they all wait "
                "together."
            ),
        ),
    ],
    "Layers": [
        (
            "layers_1",
            (
                "WebTransport keeps one connection to the server, but changes what is "
                "underneath. It runs on H-T-T-P three, the newest version of the web's "
                "protocol. That runs on Quick, and Quick runs on U-D-P."
            ),
        ),
        (
            "layers_2",
            (
                "U-D-P makes no promises at all. Packets can be lost, or arrive out of "
                "order. Quick builds reliability back on top, with encryption built "
                "in, but only where you ask for it."
            ),
        ),
    ],
    "Handshake": [
        (
            "hs_1",
            (
                "It pays off before the first message. Over T-C-P, the browser spends "
                "one round trip to open the connection, and a second to set up "
                "encryption. The WebSocket upgrade then takes a third."
            ),
        ),
        (
            "hs_2",
            (
                "Quick does the first two in a single round trip, because the "
                "encryption handshake is part of the connection handshake. One more "
                "request opens the WebTransport session, so it is ready after two "
                "round trips instead of three."
            ),
        ),
        (
            "hs_3",
            (
                "That request is an H-T-T-P CONNECT, with the protocol set to "
                "WebTransport. The server answers with status two hundred. From then "
                "on, every stream and datagram carries the I-D of that request, so the "
                "server knows which session it belongs to."
            ),
        ),
    ],
    "Streams": [
        (
            "streams_1",
            (
                "Inside the session, you open streams. Each stream is its own "
                "reliable, ordered pipe, like a small WebSocket. And opening one more "
                "costs no extra round trip."
            ),
        ),
        (
            "streams_2",
            (
                "Here is the big difference. Quick keeps the order of each stream "
                "separately. If a packet of the chat stream is lost, only chat waits. "
                "The map download, on its own stream, keeps flowing."
            ),
        ),
        (
            "streams_3",
            (
                "Streams come in two kinds. A bidirectional stream carries data both "
                "ways, like a request and its reply. A unidirectional stream goes one "
                "way only, like a file the server pushes down. Either side can open "
                "both kinds."
            ),
        ),
    ],
    "Datagrams": [
        (
            "dgram_1",
            (
                "For player positions, there is a third tool: datagrams. A datagram is "
                "one small message in one packet. It is never sent again, and it can "
                "arrive out of order, or not at all."
            ),
        ),
        (
            "dgram_2",
            (
                "That sounds worse, but look at the game again. Position four is lost. "
                "Nobody waits for it, because position five arrives about seventeen "
                "milliseconds later and replaces it. The world never freezes."
            ),
        ),
        (
            "dgram_3",
            (
                "Two limits. A datagram must fit in a single packet, about one "
                "kilobyte, so large data goes on a stream. And Quick still controls "
                "congestion, so when you send too fast, it drops datagrams instead of "
                "flooding the network."
            ),
        ),
    ],
    "Code": [
        (
            "code_1",
            (
                "In JavaScript, this takes a few lines. Create a WebTransport object "
                "with an H-T-T-P-S address, and wait until it is ready. Behind that "
                "one line, the whole handshake runs."
            ),
        ),
        (
            "code_2",
            (
                "To send a position, get a writer for the datagrams, and write a few "
                "bytes. For chat, create a bidirectional stream and write to it. To "
                "receive what the server pushes, read the incoming streams."
            ),
        ),
        (
            "code_3",
            (
                "It all uses the browser's Streams A-P-I, so backpressure is built in. "
                "When the network cannot keep up, your code is told to pause, instead "
                "of piling data up in memory."
            ),
        ),
    ],
    "Tradeoffs": [
        (
            "trade_1",
            (
                "WebTransport has costs. Some company and hotel networks block U-D-P "
                "completely. There, the connection simply fails, so real apps keep a "
                "WebSocket as a fallback."
            ),
        ),
        (
            "trade_2",
            (
                "Your server, and every load balancer in front of it, must speak "
                "H-T-T-P three and WebTransport. And it always connects a browser to a "
                "server. To connect two browsers directly, you still need Web-R-T-C."
            ),
        ),
    ],
    "Outro": [
        (
            "out_1",
            (
                "So, back to the game. Player positions travel as datagrams, and a "
                "lost one is simply replaced by the next. Chat and the map download "
                "get their own streams, so neither waits for the other."
            ),
        ),
        (
            "out_2",
            (
                "All of it shares one encrypted connection, ready in fewer round "
                "trips. That is WebTransport: your app decides, message by message, "
                "what is worth waiting for."
            ),
        ),
    ],
}
