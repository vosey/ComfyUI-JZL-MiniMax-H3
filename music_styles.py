"""JZL MiniMax Music3 — 结构化风格库（官方 12 子块对齐）

每个风格按官方 template 结构拆成三段子块：
  global      → Basic Attributes / Global Emotional Progression /
                Application Scenarios & Imagery / Sonics & Production Profile
  vocal       → Vocal Gender & Timbre / Vocal Style / Harmony-Backing Vocals / Vocal FX
  arrangement → Instrument Lifecycle (Primary/Secondary) / Groove & Foundation /
                Embellishments, Textures & Spatial FX / Section Timeline

字段均为独立完整句（句尾不带句号），由 nodes_music.py 拼接为 caption。
"""

MUSIC_STYLES = {
    "Lo-fi 嘻哈 / Lo-fi Hip-Hop": {
        "vocal": {
            "timbre": "Soft androgynous vocal with a gentle breathy timbre, sitting low in the mix like another instrument",
            "style": "Hushed half-sung half-spoken delivery with lazy behind-the-beat phrasing, leaving long stretches with no vocals at all",
            "harmony": "Sparse murmured double-tracked harmonies with occasional wordless \"mmm\" and \"ooh\" hums",
            "fx": "Drenched in tape delay and warm spring reverb",
        },
        "arrangement": {
            "primary": "Warm Rhodes piano chords with slow chorus wobble form the harmonic bed, with mellow jazzy guitar licks answering the vocal lines",
            "secondary": "Low round sub bass providing a soft foundation under the keys",
            "groove": "Dusty boom-bap drums with a soft thumping kick, cracked snare with lazy swing, and brushed hi-hats laying a relaxed pocket",
            "embellishments": "Constant vinyl crackle as texture, occasional muted trumpet ghost notes far in the background, and rain ambience",
            "timeline": "Intro: rain and vinyl noise, solo Rhodes chords fading in, drums slipping in halfway. Verses: minimal — drums, bass, Rhodes, soft guitar fills between lines. Instrumental sections: guitar and Rhodes trade relaxed jazzy phrases over the beat, occasional muted trumpet ghost notes far in the background. Bridge: drums drop away to rain, crackle, and floating detuned Rhodes, then the beat eases back in. Outro: elements fade one by one until only vinyl crackle and a last unresolved Rhodes chord remain.",
        },
    },
    "Chillhop / Chillhop": {
        "vocal": {
            "timbre": "Mostly instrumental, with no lead vocal presence",
            "style": "Rare chopped vocal samples or distant humming phrases, treated like another texture rather than a lead",
            "harmony": "Faint wordless vocal chops drifting in and out of the mix",
            "fx": "Smoothed with warm low-pass filtering and soft reverb",
        },
        "arrangement": {
            "primary": "Warm electric piano chords and airy Rhodes carrying the harmonic core",
            "secondary": "Smooth upright bass line and gentle flute accents",
            "groove": "Relaxed boom-bap drums with a soft kick and snappy rimshot snare, keeping an unhurried swing",
            "embellishments": "Filtered vinyl crackle washing over the mix and a subtle string pad swell in the chorus",
            "timeline": "Intro: filtered vinyl crackle and a slow piano riff fading in, drums joining after a few bars. Verses: minimal groove with bass, keys, and soft drum swing. Chorus: fuller keys and a subtle string pad swell. Bridge: drums strip away to keys and crackle. Outro: a final unresolved piano chord over fading vinyl.",
        },
    },
    "爵士 / Jazz": {
        "vocal": {
            "timbre": "Instrumental — no vocals at all, led by a breathy saxophone melody that sings like a voice",
            "style": "The saxophone carries a lyrical, vocal-like phrasing that substitutes for a singer",
            "harmony": "No backing vocals; comping piano chords provide the harmonic support",
            "fx": "Natural room reverb with gentle tape warmth",
        },
        "arrangement": {
            "primary": "Comping piano with sparse voicings as the harmonic bed, with a breathy saxophone stating the melody",
            "secondary": "Walking double bass anchoring the harmony and brushed drums with feather-light ride cymbal",
            "groove": "Traditional swing feel driven by walking bass and soft brushwork, unhurried and conversational",
            "embellishments": "Sparse piano voicings, brush swishes on the snare, and a single sustained sax note over the final chord",
            "timeline": "Intro: piano and bass set the changes, brushes enter softly. Head: saxophone states the melody over gentle swing. Solos: piano, then sax, trade relaxed phrases while bass walks and brushes keep time. Head reprise: melody returns, slightly ornamented. Outro: a single sustained sax note fading over a final piano chord.",
        },
    },
    "波萨诺瓦 / Bossa Nova": {
        "vocal": {
            "timbre": "Soft, breathy vocal with warm Portuguese-influenced vowel colors",
            "style": "Gentle half-whisper delivery, relaxed phrasing laid just behind the guitar rhythm",
            "harmony": "Light unison doubling on the melody, unobtrusive and airy",
            "fx": "Close-miked with natural room ambience and a touch of soft compression",
        },
        "arrangement": {
            "primary": "Nylon-string guitar playing syncopated bossa comping as the harmonic and rhythmic center",
            "secondary": "Sparse upright bass on the one and three, with whisper-quiet shaker and soft brushed drums",
            "groove": "Gentle bossa sway built on the guitar's syncopation and light percussion, breezy and unhurried",
            "embellishments": "Delicate piano phrases exchanged with the guitar, and a suspended guitar chord closing the track",
            "timeline": "Intro: solo guitar sets the groove. Verses: voice floats over guitar and bass with light percussion. Instrumental break: guitar and piano exchange gentle phrases. Outro: voice hums the melody once more, ending on a suspended guitar chord.",
        },
    },
    "灵魂乐 / Soul": {
        "vocal": {
            "timbre": "Expressive soul vocal with rich vibrato and gospel-tinged runs",
            "style": "Heartfelt phrasing that swells from a whisper to a full-bodied belt",
            "harmony": "Warm backing layers that shadow the lead and answer its phrases",
            "fx": "Drenched in warm plate reverb with gentle compression",
        },
        "arrangement": {
            "primary": "Rhodes and Hammond organ chords providing the warm harmonic core",
            "secondary": "Round electric bass and a subtle string section that swells behind the vocal",
            "groove": "Slow deep-pocket drums with a laid-back half-time feel, leaving space for the vocal",
            "embellishments": "Organ swells, string pads rising in the chorus, and ad-libbed vocal runs fading over the final chord",
            "timeline": "Intro: organ and bass establish a slow groove. Verses: voice carries the melody over minimal backing. Chorus: drums and strings swell behind a soaring vocal. Bridge: everything drops to organ and voice. Outro: ad-libbed vocal runs fading over a final chord.",
        },
    },
    "R&B / R&B": {
        "vocal": {
            "timbre": "Silky lead vocal with an intimate, close-miked tone and airy falsetto lifts",
            "style": "Modern runs and smooth phrasing, moving easily between chest voice and falsetto",
            "harmony": "Soft doubled harmonies with occasional breathy ad-libs",
            "fx": "Shimmering reverb tails with light pitch polish and subtle delay",
        },
        "arrangement": {
            "primary": "Glossy electric piano and warm pads carrying the harmonic bed",
            "secondary": "Deep 808 sub bass anchoring the low end under the trap-influenced beat",
            "groove": "Slow trap-influenced beat with rolling hi-hats and a soft punchy kick",
            "embellishments": "Filtered chord intros, breathy ad-libs between phrases, and vocal runs dissolving into reverb",
            "timeline": "Intro: filtered chords and a vocal ad-lib. Verses: sparse beat with keys and vocal. Chorus: fuller pads and stacked harmonies. Bridge: beat thins to pads and vocals. Outro: vocal runs dissolve into reverb.",
        },
    },
    "放克 / Funk": {
        "vocal": {
            "timbre": "Charismatic vocal with a punchy, forward tone sitting right on top of the groove",
            "style": "Short rhythmic phrases, shouts, and playful ad-libs delivered as call-and-response",
            "harmony": "Tight unison shouts answering the lead between phrases",
            "fx": "Dry and upfront with a light room slap",
        },
        "arrangement": {
            "primary": "Rhythmic wah-wah guitar stabs and fat analog synth chords cutting through the mix",
            "secondary": "Slapping electric bass locked hard to the kick, with bright horn section hits",
            "groove": "Tight four-on-the-floor drums with a cracking snare and relentless syncopation",
            "embellishments": "Horn punches accenting the chorus, percussion fills, and a final stabbing horn hit",
            "timeline": "Intro: drums and bass build the groove. Verses: sparse groove with vocal. Chorus: full band with horn punches. Breakdown: rhythm section only, call-and-response. Outro: a final horn hit and stop.",
        },
    },
    "嘻哈 / Hip-Hop": {
        "vocal": {
            "timbre": "Confident rap vocal with a hard-edged, forward tone",
            "style": "Sharp rhythmic flow with tight double-time passages and hard-hitting punchlines delivered with swagger",
            "harmony": "Layered ad-libs and an anthemic stacked hook on the chorus",
            "fx": "Dry and punchy with subtle ad-lib delay throws",
        },
        "arrangement": {
            "primary": "Dark piano or synth loop providing the central melodic motif",
            "secondary": "Heavy 808 bass driving the low end, with crisp snares and rolling hi-hats",
            "groove": "Heavy 808-driven beat with snapping snares and rapid hi-hat subdivisions",
            "embellishments": "Filtered loop intros, a vocal tag, and a final ad-lib ringing over the fading beat",
            "timeline": "Intro: filtered loop and a vocal tag. Verses: full rap delivery over the beat. Chorus: anthemic hook with layered vocals. Bridge: beat drops to bass and hi-hats. Outro: the loop fades with a final ad-lib.",
        },
    },
    "电子 / Electronic": {
        "vocal": {
            "timbre": "Processed vocal fragments drifting through the mix as texture",
            "style": "Reverb-soaked, heavily delayed phrases that never lead the track",
            "harmony": "Pitched vocal pads blending into the synth layers",
            "fx": "Heavy delay, subtle pitch modulation, and long reverb tails",
        },
        "arrangement": {
            "primary": "Layered synth arpeggios and airy pads carrying the melodic and harmonic movement",
            "secondary": "Pulsing analog bassline locked to the four-on-the-floor kick",
            "groove": "Steady four-on-the-floor pulse with filtered builds and tension-driven snare rolls",
            "embellishments": "Risers, filtered sweeps, and vocal fragments used as transitional textures",
            "timeline": "Intro: filtered pads build. Build-up: risers and snare rolls raise tension. Drop: full groove with driving bass. Breakdown: pads and vocal fragments. Outro: elements filter away one by one.",
        },
    },
    "氛围 / Ambient": {
        "vocal": {
            "timbre": "Instrumental — no lead vocals, only airy wordless hums and distant choir-like pads",
            "style": "Sound appears and recedes like light, without rhythm or phrasing",
            "harmony": "Distant choral pads blooming slowly beneath the drones",
            "fx": "Long reverb tails and soft dynamic swells",
        },
        "arrangement": {
            "primary": "Slow-moving pad swells forming the harmonic core, with gentle piano notes left to decay",
            "secondary": "Soft field recordings of wind and distant water providing silent texture",
            "groove": "No percussion at all; the only pulse is the slow breathing of the pads",
            "embellishments": "Long reverb tails, drifting field recordings, and a single lingering harmonic closing the piece",
            "timeline": "Opening: a single drone rises. Middle: layers of pads breathe in and out. Closing: everything dissolves into a single lingering harmonic.",
        },
    },
    "合成器浪潮 / Synthwave": {
        "vocal": {
            "timbre": "Sparse, filtered female vocal with a detached, distant quality",
            "style": "Short melodic phrases delivered like a distant radio transmission",
            "harmony": "Doubled and chorused layers thickening the hook",
            "fx": "Heavy chorus and delay with a vintage gated reverb",
        },
        "arrangement": {
            "primary": "Shimmering analog arpeggios and an anthemic synth lead carrying the melody",
            "secondary": "Pulsing analog bassline locked to the driving drum machine beat, with wide pads underneath",
            "groove": "Driving drum machine beat with steady sixteenth-note arpeggios providing momentum",
            "embellishments": "Rising arpeggios, gated reverb snares, and pads fading into a neon haze",
            "timeline": "Intro: pads and a rising arp. Verses: bass and drums lock in with vocal. Chorus: anthemic synth lead over the full groove. Bridge: everything thins to a pad. Outro: arps fade into neon haze.",
        },
    },
    "芯片音乐 / Chiptune": {
        "vocal": {
            "timbre": "Instrumental — no vocals, with bright square-wave leads singing like game themes",
            "style": "Melodies delivered with crisp, hyper-articulate chip phrasing",
            "harmony": "Pulse-width modulation chords providing the harmonic bed",
            "fx": "Authentic chip production with no reverb, only raw 8-bit clarity",
        },
        "arrangement": {
            "primary": "Square-wave lead melody as the bright, heroic focal point",
            "secondary": "Triangle-wave bassline anchoring the low end, with pulse-width modulation chords filling the middle",
            "groove": "Noise-channel hi-hats and snare driving a bouncy, relentless 8-bit pulse",
            "embellishments": "Title-screen fanfares, rapid arpeggio runs, and a final note held until it fades",
            "timeline": "Intro: title-screen fanfare. Main theme: bouncy melody over bass. Breakdown: melody thins to bass and noise. Outro: the final note holds and fades.",
        },
    },
    "浩室 / House": {
        "vocal": {
            "timbre": "Soulful sampled vocal with a warm, gospel-tinged color",
            "style": "Short chopped hooks repeated hypnotically over the groove",
            "harmony": "Stacked vocal stabs and echoed layers lifting the chorus",
            "fx": "Heavy delay throws and club-length reverb tails",
        },
        "arrangement": {
            "primary": "Warm chord stabs on electric piano providing the harmonic lift",
            "secondary": "Rolling bassline locked to the kick, with swinging hi-hats and claps",
            "groove": "Driving four-on-the-floor kick with swinging percussion and an irresistible pulse",
            "embellishments": "Filtered chord intros, risers, snare rolls, and vocal hooks echoing between drops",
            "timeline": "Intro: filtered chords and percussion build. Drop: full groove with vocal hook. Breakdown: chords and vocal alone. Build-up: risers and snare rolls. Final drop: everything returns fuller. Outro: groove strips to a kick.",
        },
    },
    "科技舞曲 / Techno": {
        "vocal": {
            "timbre": "Minimal vocals — sparse, heavily processed spoken fragments",
            "style": "Distant industrial whispers used as rhythmic texture rather than melody",
            "harmony": "No harmonic vocal layers; the vocals function as percussive elements",
            "fx": "Heavy reverb and distortion turning the voice into an industrial texture",
        },
        "arrangement": {
            "primary": "Eerie metallic synth stabs and evolving textural drones",
            "secondary": "Rolling bassline and clattering percussion layers under the pounding kick",
            "groove": "Relentless pounding kick with metallic hats and hypnotic repetitive momentum",
            "embellishments": "Industrial noise textures, reverb-drenched atmosphere, and layered percussion building tension",
            "timeline": "Intro: percussion layers build. Core: relentless groove with evolving textures. Breakdown: kick drops to a drone. Build-up: tension rises with hats. Final: groove returns harder. Outro: elements strip away to the kick.",
        },
    },
    "鼓打贝斯 / Drum & Bass": {
        "vocal": {
            "timbre": "Soulful female vocal phrases floating above the chaos",
            "style": "Pitched and chopped fragments offering brief melodic respites between drops",
            "harmony": "Aerial pad-like vocal layers suspended over the breaks",
            "fx": "Long reverb tails and pitch-shifted delay treatments",
        },
        "arrangement": {
            "primary": "Deep wobbling sub bass and syncopated stabs driving the low end",
            "secondary": "Atmospheric pads and chopped vocal textures providing the melodic relief",
            "groove": "Amen-style breakbeats at 170+ BPM with tight, intricate drum programming",
            "embellishments": "Rising risers, break fills, and atmospheric pads framing each drop",
            "timeline": "Intro: pads and vocals. Build-up: rising riser and break fills. Drop: full-speed drums and bass. Breakdown: pads and vocal. Second drop: heavier bassline. Outro: drums cut to a final sub hit.",
        },
    },
    "摇滚 / Rock": {
        "vocal": {
            "timbre": "Raspy, powerful male vocal with grit and range",
            "style": "Rising from a growl in the verses to a soaring belt in the chorus",
            "harmony": "Backing shouts and doubled layers reinforcing the anthemic chorus",
            "fx": "Slight overdrive and short room reverb keeping the performance raw",
        },
        "arrangement": {
            "primary": "Distorted power-chord guitars driving the harmonic weight, with anthemic lead riffs",
            "secondary": "Pulsing bass locked to the drums, filling the low-mid range",
            "groove": "Driving drums with a hard backbeat and steady forward momentum",
            "embellishments": "Fiery guitar solo, dynamics dropping then rebuilding in the bridge, and a final ringing chord",
            "timeline": "Intro: guitar riff kicks in. Verses: vocal over driving chords. Chorus: full band at maximum, soaring vocal. Guitar solo: melodic and fiery. Bridge: dynamics drop then rebuild. Outro: a final chord rings out.",
        },
    },
    "独立民谣 / Indie Folk": {
        "vocal": {
            "timbre": "Gentle, confessional vocal with a slight rasp, close to the mic",
            "style": "Honest, unadorned phrasing that favors storytelling over technique",
            "harmony": "Soft harmonies entering in the chorus to widen the texture",
            "fx": "Warm tape character with natural room ambience and minimal processing",
        },
        "arrangement": {
            "primary": "Fingerpicked acoustic guitar carrying melody and harmony",
            "secondary": "Soft banjo and mandolin accents, upright bass, and light brushed percussion",
            "groove": "Unhurried acoustic pulse driven by the guitar, with percussion swelling only in the chorus",
            "embellishments": "Strings drifting in during the bridge and a final guitar note ringing over silence",
            "timeline": "Intro: solo guitar melody. Verses: voice and guitar, sparse. Chorus: harmonies and light percussion swell. Bridge: strings drift in. Outro: a final guitar note rings over silence.",
        },
    },
    "原声吉他 / Acoustic": {
        "vocal": {
            "timbre": "Instrumental — no vocals, the guitar alone carrying every melody and emotion",
            "style": "Expressive fingerpicking and gentle strumming phrase the music like a voice",
            "harmony": "Chord voicings provide all harmonic support without any accompanying instrument",
            "fx": "Close-miked with warm room tone and no effects beyond gentle reverb",
        },
        "arrangement": {
            "primary": "Fingerpicked arpeggios and gentle strumming as the sole voice of the piece",
            "secondary": "A soft inner melody line woven through the chords on the upper strings",
            "groove": "Free, unhurried picking with natural rubato and no fixed tempo push",
            "embellishments": "Harmonic touches, string squeaks, and a final chord left to decay into silence",
            "timeline": "Opening: a slow picking pattern establishes the mood. Middle: the melody rises and falls. Closing: the final chord decays into silence.",
        },
    },
    "钢琴 / Piano": {
        "vocal": {
            "timbre": "Instrumental — no vocals, the piano alone singing every phrase",
            "style": "Sparse left-hand chords under a singing right-hand melody with gentle rubato",
            "harmony": "Left-hand voicings supply all harmonic depth without any other instrument",
            "fx": "Warm close-miked piano with soft pedal noise and natural decay",
        },
        "arrangement": {
            "primary": "A singing right-hand melody as the expressive center of the piece",
            "secondary": "Sparse left-hand chords and long pauses providing space and harmonic grounding",
            "groove": "Free rubato phrasing with no fixed pulse, breathing with the melody",
            "embellishments": "Soft pedal noise, gentle dynamic swells, and an unresolved chord closing the piece",
            "timeline": "Opening: a simple motif. Middle: the motif develops and swells. Closing: the opening theme returns, softer, ending on an unresolved chord.",
        },
    },
    "管弦乐 / Orchestral": {
        "vocal": {
            "timbre": "No solo vocals — an optional wordless choir rising in the climax like a distant heavenly voice",
            "style": "The choir delivers sustained, unified vocalization rather than a melodic lead",
            "harmony": "Choral layers blending into the orchestral texture at the peak",
            "fx": "Natural hall reverb with wide, cinematic spatial depth",
        },
        "arrangement": {
            "primary": "Sweeping string melodies forming the melodic spine of the score",
            "secondary": "Warm French horn chorales, woodwind colors, and timpani and cymbal accents",
            "groove": "No drum kit; momentum comes from swelling string figures and timpani rolls",
            "embellishments": "Cymbal swells, brass fanfares, and a final quiet chord dissolving into the hall",
            "timeline": "Opening: soft strings establish a theme. Build: brass and percussion swell. Climax: full orchestra at maximum. Denouement: strings alone. Ending: a final quiet chord.",
        },
    },
    "史诗 / Epic": {
        "vocal": {
            "timbre": "Powerful wordless choir chanting over the climax",
            "style": "Layered male and female voices rising like an army's anthem",
            "harmony": "Massed choir stacks widening into full ensemble blocks",
            "fx": "Huge hall reverb with dramatic dynamic swells",
        },
        "arrangement": {
            "primary": "Thundering taiko drums and relentless string ostinatos driving the momentum",
            "secondary": "Blaring brass fanfares and choir swells filling the upper spectrum",
            "groove": "Martial taiko pulse with insistent ostinato figures building step by step",
            "embellishments": "Cymbal crashes, choir stabs, and a final drum hit cutting to silence",
            "timeline": "Opening: low strings and drums build. Rises: tension climbs step by step. Climax: full choir and orchestra explode. Aftermath: strings fade. Ending: a final drum hit and silence.",
        },
    },
    "浪漫弦乐 / Romantic Strings": {
        "vocal": {
            "timbre": "Instrumental — no vocals, the strings themselves sing with aching lyricism",
            "style": "Sweeping legato lines delivered with warm vibrato",
            "harmony": "Cello and viola harmonies supporting the soaring violins",
            "fx": "Gentle hall reverb and warm vibrato creating a lush sustain",
        },
        "arrangement": {
            "primary": "Lush violin melody soaring in unison over warm cello and viola harmonies",
            "secondary": "Harp glissandos and delicate pizzicato adding color beneath the line",
            "groove": "Flowing waltz-like sway with no percussion, led entirely by the bowing",
            "embellishments": "Harp glissandos, pizzicato accents, and the melody dissolving into a single held note",
            "timeline": "Opening: cello introduces a theme. Middle: violins soar in unison. Swell: full section in passionate vibrato. Ending: the melody dissolves into a single held note.",
        },
    },
    "悬疑 / Suspense": {
        "vocal": {
            "timbre": "Instrumental — no vocals, only eerie wordless whispers and distant humming",
            "style": "Voices used as unsettling texture rather than melody",
            "harmony": "Dissonant clusters replacing conventional harmonic support",
            "fx": "Close-miked textures, deep drones, and sudden silences",
        },
        "arrangement": {
            "primary": "Low-frequency drones and dissonant string clusters holding the tension",
            "secondary": "Sparse piano notes and ticking percussion emerging from the texture",
            "groove": "No groove; a heartbeat-like pulse drives the creeping unease",
            "embellishments": "Sudden dissonant stabs, deep silences, and an unresolved note hanging at the end",
            "timeline": "Opening: a low drone and a heartbeat pulse. Build: textures layer and tighten. Stabs: sudden dissonant hits. Release: silence, then a whisper. Ending: an unresolved note hangs.",
        },
    },
    "国风民乐 / Chinese Folk": {
        "vocal": {
            "timbre": "Ethereal female vocal with soft vibrato, singing in a pentatonic register",
            "style": "Delicate melodic phrasing like a distant mountain song, with occasional wordless humming",
            "harmony": "Light unison doubling and airy responses that never crowd the melody",
            "fx": "Natural room ambience preserving the raw timbre of the voice",
        },
        "arrangement": {
            "primary": "Guzheng glissandos and erhu melodic lines forming the emotional core",
            "secondary": "Dizi bamboo flute trills and pipa tremolos adding color and motion",
            "groove": "Free-flowing rubato led by plucked-string motion, with no drum kit",
            "embellishments": "Guzheng echo tails, dizi trills, and a final flute phrase fading away",
            "timeline": "Opening: guzheng sets a flowing texture. Theme: erhu and flute trade phrases. Middle: pipa adds rhythmic color. Ending: flute fades over a guzheng echo.",
        },
    },
    "古琴 / Guqin": {
        "vocal": {
            "timbre": "No vocals — only the guqin's resonant strings and soft harmonic overtones",
            "style": "Phrases unfold like breath, with long silences between notes",
            "harmony": "Occasional soft harmonic overtones supply the only harmonic shading",
            "fx": "Intimate close-miking capturing every string texture and finger slide",
        },
        "arrangement": {
            "primary": "Slow, sparse plucked phrases on the guqin with long silences between notes",
            "secondary": "Subtle slides and harmonic overtones adding depth to the silence",
            "groove": "No pulse at all; the music breathes in long, meditative gaps",
            "embellishments": "Finger slides, harmonic chimes, and phrases dissolving into silence",
            "timeline": "Opening: a single deep note. Middle: phrases unfold like breath. Closing: harmonics fade into silence.",
        },
    },
    "戏曲 / Chinese Opera": {
        "vocal": {
            "timbre": "Piercing theatrical vocal with a bright, cutting tone",
            "style": "Alternating between dramatic declamation and high falsetto, ornamented with vibrato and slides",
            "harmony": "Unison responses from the ensemble punctuating the declamation",
            "fx": "Unprocessed live-stage vocal with bright natural acoustics",
        },
        "arrangement": {
            "primary": "Piercing erhu lines and bamboo flute carrying the melodic drama",
            "secondary": "Clanging gongs and wooden clappers driving the theatrical punctuation",
            "groove": "Striking percussion accents marking the recitation rather than a steady beat",
            "embellishments": "Gong crashes, clapper rolls, and a final clap cutting to silence",
            "timeline": "Opening: gong and clappers announce. Recitation: vocal declaims over sparse percussion. Aria: full band with expressive vocal. Climax: gongs crash. Ending: a final clap and silence.",
        },
    },
    "冥想 / Meditation": {
        "vocal": {
            "timbre": "Soft wordless humming and long vowel tones, like a gentle chant",
            "style": "Sustained, non-rhythmic vocalization floating above the drones",
            "harmony": "Low choral drones beneath the humming, never taking focus",
            "fx": "Long, soft reverb tails with no sharp transients",
        },
        "arrangement": {
            "primary": "Singing bowls and slow drone pads forming the harmonic ground",
            "secondary": "Soft wind chimes and a distant flute adding gentle movement",
            "groove": "No percussion or pulse; the music moves only in slow swells",
            "embellishments": "Singing bowl rings, chime shimmer, and a fading drone leaving one pure tone",
            "timeline": "Opening: a singing bowl rings. Middle: drones and bowls layer softly. Closing: everything fades to a single pure tone.",
        },
    },
    "自然白噪音 / Nature Ambient": {
        "vocal": {
            "timbre": "No vocals — only birdsong and wind carry the soundscape",
            "style": "No melodic phrasing; the field recording itself is the performance",
            "harmony": "No harmonic content, only layered natural ambience",
            "fx": "Untouched field-recording textures with gentle spatial depth",
        },
        "arrangement": {
            "primary": "Layered field recordings of rain and wind through trees forming the bed",
            "secondary": "Distant thunder, birdsong, and crickets adding depth to the scene",
            "groove": "No melody or beat; only the natural rhythm of weather and wildlife",
            "embellishments": "Rain intensity shifting, distant birds answering each other, and rain fading out alone",
            "timeline": "Opening: rain fades in. Middle: birds and wind join. Closing: rain alone, fading softly.",
        },
    },
    "华语流行 / Mandopop": {
        "vocal": {
            "timbre": "Warm, expressive Chinese vocal with clear diction and gentle vibrato",
            "style": "Emotional phrasing that rises from intimate verses into an open, soaring chorus",
            "harmony": "Soft doubled harmonies and airy backing layers widening the chorus",
            "fx": "Polished modern vocal chain with tasteful reverb and light pitch correction",
        },
        "arrangement": {
            "primary": "Warm electric piano and glossy synth pads forming the harmonic bed, with subtle guitar arpeggios",
            "secondary": "Round bassline and crisp drums anchoring the mid-tempo pop beat",
            "groove": "Mid-tempo pop beat with crisp drums and an even, driving pocket",
            "embellishments": "Filtered keys, rising pads in the pre-chorus, and stacked harmonies on the hook",
            "timeline": "Intro: filtered keys and a soft vocal breath. Verses: minimal beat with keys and vocal. Pre-chorus: tension builds with rising pads. Chorus: full band, soaring vocal, stacked harmonies. Bridge: everything thins to piano and voice. Outro: the hook fades over a final chord.",
        },
    },
    "国风流行 / Guofeng Pop": {
        "vocal": {
            "timbre": "Ethereal, emotive vocal with soft vibrato and delicate ornamentation",
            "style": "Flowing legato delivery with occasional airy falsetto",
            "harmony": "Gentle layered harmonies shadowing the melody",
            "fx": "Modern ballad reverb blended with traditional room warmth",
        },
        "arrangement": {
            "primary": "Piano and guzheng sharing the harmonic bed, with erhu melodic lines",
            "secondary": "Dizi flute accents and subtle electronic pads over a slow pop beat",
            "groove": "Slow pop beat with drums entering only at the chorus",
            "embellishments": "Guzheng glissando responses, dizi filigree, and a single guzheng note closing the track",
            "timeline": "Intro: guzheng glissando over piano. Verses: sparse piano and vocal with guzheng echoes. Chorus: drums enter with strings and dizi, vocal soars. Bridge: erhu solo over pads. Outro: a single guzheng note fades.",
        },
    },
    "流行 / Pop": {
        "vocal": {
            "timbre": "Clear, confident lead vocal with a bright, radio-friendly tone",
            "style": "Strong hook delivery with punchy, well-articulated phrasing",
            "harmony": "Layered harmonies and ad-libs fattening the chorus",
            "fx": "Subtly pitch-polished with crisp modern reverb and delay",
        },
        "arrangement": {
            "primary": "Sparkling synths and rhythmic guitar carrying the hook",
            "secondary": "Punchy bass and crisp drums driving the upbeat pop beat",
            "groove": "Upbeat pop beat with a tight, energetic pocket",
            "embellishments": "Hooky instrumental riff, pre-chorus tension builds, and stacked harmonies on the final chorus",
            "timeline": "Intro: hooky instrumental riff. Verses: sparse beat with vocal. Pre-chorus: tension builds. Chorus: massive hook with stacked harmonies. Bridge: stripped-back moment. Final chorus: everything returns bigger. Outro: the hook fades out.",
        },
    },
    "金属 / Metal": {
        "vocal": {
            "timbre": "Harsh, powerful vocal with a guttural growl and a soaring melodic clean tone",
            "style": "Alternating between growled verses and melodic clean choruses at maximum intensity",
            "harmony": "Gang shouts reinforcing the heaviest sections",
            "fx": "Raw and aggressive with minimal processing, keeping the attack intact",
        },
        "arrangement": {
            "primary": "Palm-muted chugging riffs and screaming lead guitar driving the harmonic weight",
            "secondary": "Roaring bass locked to the double-kick pattern, filling the bottom end",
            "groove": "Driving double-kick drums with crushing half-time breakdowns",
            "embellishments": "Fast technical guitar solo, abrupt stops, and a final chug cutting off hard",
            "timeline": "Intro: a fast riff and drum fill kick in. Verses: chugging guitars under growled vocals. Chorus: melodic clean vocal over soaring chords. Breakdown: half-time heaviness. Guitar solo: fast and technical. Outro: a final chug ends abruptly.",
        },
    },
    "布鲁斯 / Blues": {
        "vocal": {
            "timbre": "Weathered, gravelly vocal full of bent notes and character",
            "style": "Heartfelt phrasing alternating between a spoken growl and a full-throated wail",
            "harmony": "Call-and-response answers from the guitar and harmonica rather than backing voices",
            "fx": "Warm tube amp character with natural room ambience, unpolished and honest",
        },
        "arrangement": {
            "primary": "Expressive lead guitar fills answering the vocal line",
            "secondary": "Walking bass and rhythmic rhythm guitar holding the twelve-bar changes, with harmonica accents",
            "groove": "Relaxed shuffle drums with a slow-burning, behind-the-beat swing",
            "embellishments": "Smoky harmonica and guitar solo trade-offs, and a final bent note winding the band down",
            "timeline": "Intro: a slow bluesy guitar riff. Verses: vocal over the shuffle with guitar answers. Solos: smoky, bluesy guitar and harmonica trade phrases. Outro: the band winds down to a final bent note.",
        },
    },
    "乡村 / Country": {
        "vocal": {
            "timbre": "Warm, twangy vocal with a slight southern drawl",
            "style": "Sincere, storytelling delivery that stays conversational throughout",
            "harmony": "Tight close harmonies joining on the chorus",
            "fx": "Natural room ambience with gentle compression and light reverb",
        },
        "arrangement": {
            "primary": "Acoustic and electric guitars with pedal steel swells forming the core",
            "secondary": "Fiddle accents and upright bass supporting the strummed foundation",
            "groove": "Steady backroad shuffle with brushed snare and an easy two-step feel",
            "embellishments": "Pedal steel solo in the bridge, fiddle fills, and a fade where guitar and steel drift away together",
            "timeline": "Intro: acoustic guitar and pedal steel. Verses: vocal over strumming. Chorus: full band with harmonies and fiddle. Bridge: pedal steel solo. Outro: guitar and steel fade together.",
        },
    },
    "摇摆爵士 / Swing & Big Band": {
        "vocal": {
            "timbre": "Charismatic crooner vocal with a warm, rounded tone",
            "style": "Effortless swing phrasing with playful scat syllables and call-and-response with the band",
            "harmony": "Section responses from the horns echoing the vocal phrases",
            "fx": "Vintage mono warmth with bright brass and natural room reverb",
        },
        "arrangement": {
            "primary": "Tight brass section with trumpets, trombones, and saxophones driving the arrangement",
            "secondary": "Swinging rhythm guitar, walking bass, and crisp hi-hat drums locking the pocket",
            "groove": "Bouncy swing feel with a tight, propulsive rhythm section",
            "embellishments": "Solo trades between trumpet, sax, and trombone, and a shout chorus before the final brass stab",
            "timeline": "Intro: full band hits a swinging riff. Head: vocal over the swing. Solos: trumpet, sax, and trombone trade phrases. Final chorus: shout chorus with the full band. Outro: a final brass stab.",
        },
    },
    "迪斯科 / Disco": {
        "vocal": {
            "timbre": "Smooth, soaring vocal with rich harmonies and falsetto lifts",
            "style": "Delivered with disco flair and echoed call-and-response phrases",
            "harmony": "Lush stacked harmonies and echoed choral answers",
            "fx": "Shimmering reverb and rhythmic delay throws widening the vocal",
        },
        "arrangement": {
            "primary": "Lush string section and wah-wah rhythm guitar glittering over the groove",
            "secondary": "Walking octave bass and bright horns locking the dance-floor pulse",
            "groove": "Four-on-the-floor kick with a hypnotic walking bass and shimmering percussion",
            "embellishments": "String swells, horn stabs, and a percussion breakdown before the final chorus",
            "timeline": "Intro: strings and bass build. Verses: vocal over the pulse. Chorus: full band with strings and harmonies. Breakdown: percussion and bass. Final chorus: everything returns bigger. Outro: a final string hit.",
        },
    },
    "出神 / Trance": {
        "vocal": {
            "timbre": "Ethereal female vocal floating above the mix",
            "style": "Reverb-drenched phrases providing brief melodic hooks between the drops",
            "harmony": "Airy harmonized layers suspended over the pads",
            "fx": "Epic reverb and long delay tails",
        },
        "arrangement": {
            "primary": "Sweeping supersaw pads and shimmering arpeggios forming the harmonic wall",
            "secondary": "Rolling bassline locked to the driving kick, with emotional piano in the breakdown",
            "groove": "Driving four-on-the-floor kick with rolling bass and relentless forward motion",
            "embellishments": "Long builds, snare rolls, and epic reverb-drenched breakdowns",
            "timeline": "Intro: pads and arps build. Breakdown: vocal and pads with a long build. Drop: full supersaw wall of sound. Second breakdown: emotional piano and vocal. Final drop: everything returns euphoric. Outro: pads fade into silence.",
        },
    },
    "雷鬼 / Reggae": {
        "vocal": {
            "timbre": "Relaxed, soulful vocal with a warm, unhurried tone",
            "style": "Melodic, conversational delivery with an easy island sway",
            "harmony": "Occasional harmony backing that lifts the chorus",
            "fx": "Analog warmth with dub echo accents",
        },
        "arrangement": {
            "primary": "Offbeat skank guitar and bright organ stabs defining the groove",
            "secondary": "Deep round bassline and one-drop drums with rimshot accents",
            "groove": "Laid-back one-drop with the emphasis on the third beat and a sun-soaked swing",
            "embellishments": "Melodica or guitar solo, dub echo throws, and a groove fading into echo",
            "timeline": "Intro: bass and skank set the groove. Verses: vocal floats over the one-drop. Chorus: harmonies lift. Instrumental: melodica or guitar solo. Outro: groove fades into dub echo.",
        },
    },
    "福音 / Gospel": {
        "vocal": {
            "timbre": "Powerful lead vocal with gospel runs and a soaring tone",
            "style": "Alternating between solo verses and full-chorus swells with call-and-response",
            "harmony": "Lush choir with tight four-part harmonies answering the lead",
            "fx": "Warm live production with natural room reverb and rich choral blend",
        },
        "arrangement": {
            "primary": "Hammond organ swells and piano carrying the harmonic weight",
            "secondary": "Walking bass, rhythmic handclaps, and a full choir filling the spectrum",
            "groove": "Swaying church groove with handclaps and a steadily building pulse",
            "embellishments": "Organ swells, handclaps, and a final soaring vocal run fading into a held chord",
            "timeline": "Intro: organ and a solo vocal line. Verses: call-and-response between lead and choir. Chorus: full choir in stacked harmonies with handclaps. Bridge: everything drops to organ and a cappella voices. Outro: a final soaring vocal run fading into a held chord.",
        },
    },
    "阿卡贝拉 / A Cappella": {
        "vocal": {
            "timbre": "Layered human voices with a clear lead and tight four-part harmonies",
            "style": "Pure vocal performance with no instruments, alternating lead and ensemble sections",
            "harmony": "Rich four-part harmony stacks with a dedicated vocal bass line",
            "fx": "Close-miked voices with natural ambience and crisp vocal clarity",
        },
        "arrangement": {
            "primary": "The human voice carries every melodic and harmonic role",
            "secondary": "Vocal bass line and mouth-percussion (beatbox) replacing the rhythm section",
            "groove": "Percussive consonant articulation and beatbox patterns providing the entire pulse",
            "embellishments": "Wordless vocal pads, dynamic swell through layering, and voices fading one by one into a final chord",
            "timeline": "Intro: a vocal bass groove. Verses: lead voice over harmony pads. Chorus: full vocal stack in rich harmony. Breakdown: solo voice and beatbox. Outro: voices fade one by one into a final held chord.",
        },
    },
}
