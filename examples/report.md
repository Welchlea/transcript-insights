# Chatbot transcript report

400 conversations.

## What to fix first

1. Review the 'take_money_out' journey. 39% of users leave without an answer (37 of 96).
2. Rewrite or split the 'explain_tax' step. 24% of all abandoned conversations end there (26 of 110).
3. Teach the bot these messages, or add them to an existing topic: "can i take a lump sum" (52), "transfer my pension to another provider" (25), "what is my tax code" (18).
4. Offer a person after the first unclear answer. 41 users got two fallbacks in a row and 100% of them did not get an answer from the bot.
5. 17% of conversations never matched a topic. Check the welcome message says what the bot can help with.

## Headline measures

| Measure | Value | What it means |
| --- | --- | --- |
| Containment | 58% | Resolved by the bot, leaving out handovers that are by design |
| Resolved | 52% | The user got what they came for from the bot |
| Handed over | 20% | Passed to a person. 41 of 81 were by design |
| Abandoned | 28% | The user left part way through |
| Fallback rate | 11% | Bot messages that were 'I did not understand' |
| Average length | 5.7 | Messages in a conversation, from both sides |

## By topic

| Topic | Conversations | Resolved | Handed over | Abandoned |
| --- | --- | --- | --- | --- |
| check_balance | 122 | 85% | 4% | 11% |
| take_money_out | 96 | 45% | 17% | 39% |
| change_address | 73 | 85% | 8% | 7% |
| not recognised | 68 | 0% | 19% | 81% |
| report_death | 21 | 0% | 100% (by design) | 0% |
| complaint | 20 | 0% | 100% (by design) | 0% |

## Where users give up

| Last bot step before the user left | Conversations |
| --- | --- |
| a fallback message | 55 |
| explain_tax | 26 |
| confirm_identity | 22 |
| check_age | 6 |
| ask_postcode | 1 |

## What the bot did not understand

| User message | Times |
| --- | --- |
| can i take a lump sum | 52 |
| transfer my pension to another provider | 25 |
| what is my tax code | 18 |
| is this a scam | 12 |
| agent | 11 |

## Repeated fallbacks

41 conversations had two or more fallbacks in a row. 100% of those were not resolved by the bot.
