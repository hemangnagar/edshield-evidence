Name mentions missed by at least three of the 5 primary detectors (edshield, presidio, spacy_trf, hf_pii, gpt4o_mini), all seeds: 1544. By number of detectors that missed: 3 detectors: 665, 4 detectors: 611, 5 detectors: 268.

| stratum | form | shared misses |
|---|---|---|
| upper|tutor|nondict | initial | 689 |
| upper|tutor|dict | name | 340 |
| upper|tutor|nondict | name | 144 |
| upper|student|nondict | initial | 127 |
| upper|student|dict | name | 102 |
| lower|student|dict | name | 66 |
| lower|student|nondict | name | 43 |
| upper|student|nondict | name | 33 |

First example per stratum and form (lowest seed, then document order), most detectors first:

- `to time? Student: 2xda/dt+2ydb/dt. my cousin [[product]] says you have to flip it` — comta comta-013, seed 20261014, lower|student|dict, name_word_collision; missed by edshield, presidio, spacy_trf, hf_pii, gpt4o_mini.
- `the hexagon problem Tutor: You're close, [[T.]] . Alright! If you're finished with` — comta comta-016, seed 20261014, upper|tutor|nondict, initial, non_anglo; missed by edshield, presidio, spacy_trf, hf_pii, gpt4o_mini.
- `Student: hey its [[vee]] . Can you provide me with` — comta comta-031, seed 20261014, lower|student|nondict, nicknames_and_variants; missed by edshield, presidio, spacy_trf, hf_pii, gpt4o_mini.
- `Tutor: Hi Adam, can you walk me through your maths? Student: [[A.]] here. Sure, I started by calculating the total interest that Karan had to pay. I multiplied the principal amount of` — mathdial mathdial-test-046, seed 20261014, upper|student|nondict, initial, anglo_common; missed by edshield, presidio, spacy_trf, hf_pii, gpt4o_mini.
- `Tutor: Hey Cameron, can you work me through your solution please? Student: [[Came]] here. Sure. I started by calculating the total duration of the original 25 songs, which is 25 x 3 =` — mathdial mathdial-test-210, seed 20261014, upper|student|dict, anglo_common; missed by edshield, presidio, spacy_trf, hf_pii, gpt4o_mini.
- `so if there are four lanes, and 60 trucks in each lane, how many trucks are there overall? Keep going, [[Summer]] . Student: There would be 4*60 = 240 trucks overall. Tutor: correct, and so if there are twice as many` — mathdial mathdial-test-266, seed 20261014, upper|tutor|dict, name_word_collision; missed by edshield, presidio, spacy_trf, hf_pii, gpt4o_mini.
- `of post-it notes she used (277). This gave me the number of post-it notes she bought (197). Tutor: Nice work, [[Dr]] . Let's think again about the cups that Candice labelled. How many cups did she label and how many post` — mathdial mathdial-test-108, seed 20261016, upper|tutor|nondict, nicknames_and_variants; missed by edshield, presidio, spacy_trf, hf_pii, gpt4o_mini.
- `Tutor: Hi Diego, Can you walk me through your solution? Student: [[DIEGO]] here. Sure. I started by figuring out how many gallons of gas were left in the tank. I knew that` — mathdial mathdial-test-043, seed 20261014, upper|student|nondict, non_anglo; missed by presidio, spacy_trf, hf_pii, gpt4o_mini.
