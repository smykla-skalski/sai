"""Narration, one clip per beat: {scene class: [(clip key, spoken text), ...]}.

Keys are used in video.py. The text is only spoken, never shown, so it is written for
the ear. Acronyms are spelled with hyphens so the voice reads them letter by letter:
"Open I-D Connect", "O-I-D-C", "I-D token", "J-W-T", "P-K-C-E". "O-Auth" keeps the
voice from saying "oath".

Copyright 2026 Smykla Skalski, MIT License.
"""

from typing import Final

BEATS: Final = {
    "Hook": [
        (
            "hook_1",
            (
                "You click Sign in with Google on a site you have never used before. A "
                "second later, the site greets you by name, and you never typed a "
                "password there."
            ),
        ),
        (
            "hook_2",
            (
                "So how does the site know that it is really you? The answer is a "
                "protocol called Open I-D Connect, or O-I-D-C. Let's draw how it "
                "works."
            ),
        ),
    ],
    "Trust": [
        (
            "trust_1",
            (
                "The core idea is old. At a border, the officer has never met you. "
                "Instead, they trust a passport, issued by a government they already "
                "trust, and they check that it is genuine."
            ),
        ),
        (
            "trust_2",
            (
                "Open I-D Connect does the same thing for the web. The site plays the "
                "officer, an identity provider plays the government, and the passport "
                "is a signed message called an I-D token."
            ),
        ),
    ],
    "OAuth": [
        (
            "oauth_1",
            (
                "Open I-D Connect is built on top of an older protocol, O-Auth two. "
                "O-Auth answers a different question. Not who you are, but what an app "
                "may do on your behalf."
            ),
        ),
        (
            "oauth_2",
            (
                "Its access token works like a hotel key card. It opens certain doors, "
                "but it says nothing about the person who holds it. Apps that used it "
                "as proof of identity had real security holes."
            ),
        ),
        (
            "oauth_3",
            (
                "So Open I-D Connect adds one thin layer. Ask for the scope called "
                "open I-D, and next to the access token you also get an I-D token, a "
                "statement about who just logged in."
            ),
        ),
    ],
    "Flow": [
        (
            "flow_1",
            (
                "Three parties take part. You, in your browser. The app you want to "
                "use, which the standard calls the relying party. And the identity "
                "provider, the only one that knows your password."
            ),
        ),
        (
            "flow_2",
            (
                "When you click the button, the app sends your browser to the "
                "provider, with a request packed into the address. It names the app, "
                "where to return, the scopes it wants, and two random values, called "
                "state and nonce."
            ),
        ),
        (
            "flow_3",
            (
                "The provider checks who you are, with your password and maybe a "
                "second factor. Then it asks if you agree to share your name and email "
                "with this app."
            ),
        ),
        (
            "flow_4",
            (
                "Then it sends your browser back to the app, carrying only a short, "
                "one-time code. The browser is a risky place, because addresses end up "
                "in history and in logs, so this code alone is worth very little."
            ),
        ),
        (
            "flow_5",
            (
                "Now the app calls the provider directly, server to server, and trades "
                "the code plus its own secret for the tokens. This back channel never "
                "touches the browser."
            ),
        ),
    ],
    "Token": [
        (
            "token_1",
            (
                "Here is an I-D token. It is a J-W-T, a JSON web token. Three blocks "
                "of encoded text, joined by dots. A header, a payload, and a "
                "signature."
            ),
        ),
        (
            "token_2",
            (
                "Decode the payload and you find claims. The issuer says who made the "
                "token. The subject is a stable identifier for you. The audience is "
                "the app that the token was made for."
            ),
        ),
        (
            "token_3",
            (
                "Then the expiry time, the nonce from the request, and finally your "
                "name and email. But anyone can type text like this. What makes it "
                "trustworthy is the signature."
            ),
        ),
    ],
    "Signature": [
        (
            "sig_1",
            (
                "The provider keeps a private key secret. It publishes the matching "
                "public key at a well-known address, next to its other settings, and "
                "the app downloads it once."
            ),
        ),
        (
            "sig_2",
            (
                "Let's sign with tiny numbers. The public key is the pair thirty-three "
                "and three. The private key is seven. Say the payload hashes to four. "
                "The signature is four to the power seven, modulo thirty-three, which "
                "is sixteen."
            ),
        ),
        (
            "sig_3",
            (
                "To verify, the app needs only the public numbers. Sixteen cubed, "
                "modulo thirty-three, is four. That equals the hash, so this exact "
                "payload was signed by whoever holds the seven."
            ),
        ),
        (
            "sig_4",
            (
                "Now change one letter of the payload. Its hash changes too, say to "
                "five. But sixteen cubed is still four, so the check fails, and the "
                "app rejects the token."
            ),
        ),
        (
            "sig_5",
            (
                "To forge a signature, you would need the private key, and finding it "
                "means splitting thirty-three into three times eleven. Easy here. Real "
                "keys use numbers with more than six hundred digits."
            ),
        ),
    ],
    "Checks": [
        (
            "check_1",
            (
                "A valid signature is only the first check. The app also confirms that "
                "the issuer is the provider it expects, that the token has not "
                "expired, and that the audience is its own client I-D."
            ),
        ),
        (
            "check_2",
            (
                "The audience check matters more than it looks. Say a shady quiz app "
                "also offers Sign in with Google, and collects real, signed tokens "
                "from its users. Without the audience check, it could replay one at "
                "your bank."
            ),
        ),
        (
            "check_3",
            (
                "The nonce does the same job in time. The app made it up at the start "
                "of this very login, so a token copied from an earlier login carries "
                "the wrong nonce, and is rejected. The state value guards the return "
                "trip the same way."
            ),
        ),
    ],
    "Pkce": [
        (
            "pkce_1",
            (
                "Phone apps and single page apps cannot keep a secret, so a stolen "
                "code would be enough. The fix is called P-K-C-E. Before the redirect, "
                "the app picks a random verifier, and sends only its hash."
            ),
        ),
        (
            "pkce_2",
            (
                "When the app trades the code, it reveals the verifier. The provider "
                "hashes it and compares. An attacker who grabbed the code from the "
                "browser never saw the verifier, so the code is useless to them."
            ),
        ),
    ],
    "Outro": [
        (
            "out_1",
            (
                "One last rule. Identify users by the issuer and the subject together, "
                "never by email, because an email address can change, or move to "
                "someone else."
            ),
        ),
        (
            "out_2",
            (
                "So, back to that button. A redirect to the provider, a one-time code, "
                "a swap on the back channel, and a signed token that the app checks "
                "before it believes a word. That is how the site knows it is you."
            ),
        ),
    ],
}
