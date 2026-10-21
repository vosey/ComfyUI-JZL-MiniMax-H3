"""JZL MiniMax Music3 — 多风格 caption 前置节点（V1 经典 API）

输出官方三段式英文 caption（Global Metadata / Vocal Details / Arrangement），
STRING 可直接接到官方「MiniMax Music3 Text Encode」的 caption 输入。

官方参考: comfy_extras/nodes_minimax_music.py — MiniMaxMusic3TextEncode
caption 规范: comfy/ldm/minimax_music/prompt.py — clean_caption / build_prompt
"""

import re

try:
    from .music_styles import MUSIC_STYLES
except ImportError:  # 以文件方式直接加载时的兜底
    from music_styles import MUSIC_STYLES


class JZL_MiniMaxMusicCaption:
    """MiniMax Music3 提示词预设 — 多维度标签 → 三段式 caption"""

    # ═══════════════════════════════════════════════════════════
    #  音乐风格库（每个风格三段：global / vocal / arrangement）
    #  写法密度对齐官方 Lo-fi 参考范例
    # ═══════════════════════════════════════════════════════════

    _STYLES = {
        "Lo-fi 嘻哈 / Lo-fi Hip-Hop": {
            "global": "Lo-fi hip-hop, chillhop. Laid-back and dreamy throughout, a gentle warm drift with a subtle late-night glow that deepens in the middle and dissolves softly at the end. Studying, raining-outside, headphones-on late-night listening. Bedroom production: muddy warm texture, heavy vinyl crackle, tape hiss and wow-flutter pitch wobble, low-passed dusty mix, soft-clipped drums, everything slightly detuned and cozy.",
            "vocal": "Soft androgynous vocal, hushed half-sung half-spoken delivery, sitting low in the mix like another instrument, lazy behind-the-beat phrasing, gentle breathy timbre. Sparse murmured double-tracked harmonies, occasional wordless \"mmm\" and \"ooh\" hums drenched in tape delay and warm spring reverb. Long stretches with no vocals at all.",
            "arrangement": "Dusty boom-bap drums with a soft thumping kick, cracked snare with lazy swing, brushed hi-hats, low round sub bass. Warm Rhodes piano chords with slow chorus wobble as the harmonic bed, mellow jazzy guitar licks answering the vocal lines, constant vinyl crackle as texture. Intro: rain and vinyl noise, solo Rhodes chords fading in, drums slipping in halfway. Verses: minimal — drums, bass, Rhodes, soft guitar fills between lines. Instrumental sections: guitar and Rhodes trade relaxed jazzy phrases over the beat, occasional muted trumpet ghost notes far in the background. Bridge: drums drop away to rain, crackle, and floating detuned Rhodes, then the beat eases back in. Outro: elements fade one by one until only vinyl crackle and a last unresolved Rhodes chord remain.",
        },
        "Chillhop / Chillhop": {
            "global": "Chillhop, laid-back instrumental hip-hop. Smooth and unhurried throughout, a mellow late-afternoon glow that stays even and warm from start to finish. Coffee-shop study sessions, rainy-window ambience. Polished lo-fi production: warm rounded bass, soft vinyl crackle, gently low-passed mix, cozy and intimate.",
            "vocal": "Mostly instrumental. If vocals appear, they are rare chopped vocal samples or distant humming phrases, treated like another texture rather than a lead, drifting in and out of the mix.",
            "arrangement": "Relaxed boom-bap drums with a soft kick and snappy rimshot snare, smooth upright bass line, warm electric piano chords, airy Rhodes and gentle flute accents. Intro: filtered vinyl crackle and a slow piano riff fading in, drums joining after a few bars. Verses: minimal groove with bass, keys, and soft drum swing. Chorus: fuller keys and a subtle string pad swell. Bridge: drums strip away to keys and crackle. Outro: a final unresolved piano chord over fading vinyl.",
        },
        "爵士 / Jazz": {
            "global": "Acoustic jazz trio. Warm and sophisticated throughout, smoky and intimate, evoking a dimly lit late-night club. Sipping whisky, low chatter, velvet curtains. Warm analog production: natural room reverb, gentle tape warmth, softly rounded transients.",
            "vocal": "No vocals — a pure instrumental jazz performance led by a breathy saxophone melody that sings like a voice.",
            "arrangement": "Walking double bass, brushed drums with feather-light ride cymbal, comping piano with sparse voicings. Intro: piano and bass set the changes, brushes enter softly. Head: saxophone states the melody over gentle swing. Solos: piano, then sax, trade relaxed phrases while bass walks and brushes keep time. Head reprise: melody returns, slightly ornamented. Outro: a single sustained sax note fading over a final piano chord.",
        },
        "波萨诺瓦 / Bossa Nova": {
            "global": "Bossa nova. Light, breezy, and effortlessly elegant throughout, a gentle seaside afternoon sway. Ocean breeze, sun-dappled terrace, soft clinking glasses. Warm analog production: close-miked nylon guitar, natural room ambience, softly compressed and smooth.",
            "vocal": "Soft, breathy vocal delivered in a gentle half-whisper, relaxed phrasing laid just behind the guitar rhythm, with warm Portuguese-influenced vowel colors.",
            "arrangement": "Nylon-string guitar playing syncopated bossa comping, sparse upright bass on the one and three, whisper-quiet shaker, soft brushed drums. Intro: solo guitar sets the groove. Verses: voice floats over guitar and bass with light percussion. Instrumental break: guitar and piano exchange gentle phrases. Outro: voice hums the melody once more, ending on a suspended guitar chord.",
        },
        "灵魂乐 / Soul": {
            "global": "Classic soul. Warm, rich, and deeply emotional throughout, a slow-burning late-night heartbreak glow. Dimly lit lounge, velvet seats, quiet intimacy. Warm analog production: tube warmth, gentle tape saturation, soft room reverb.",
            "vocal": "Expressive soul vocal with rich vibrato, gospel-tinged runs, and heartfelt phrasing that swells from a whisper to a full-bodied belt, drenched in warm plate reverb.",
            "arrangement": "Slow deep-pocket drums, round electric bass, Rhodes and Hammond organ chords, subtle string section swells. Intro: organ and bass establish a slow groove. Verses: voice carries the melody over minimal backing. Chorus: drums and strings swell behind a soaring vocal. Bridge: everything drops to organ and voice. Outro: ad-libbed vocal runs fading over a final chord.",
        },
        "R&B / R&B": {
            "global": "Contemporary R&B. Smooth, seductive, and polished throughout, a late-night neon glow with a slow pulse. City lights, silk sheets, intimate and hazy. Clean modern production: deep sub bass, tight drums, glassy keys, shimmering reverb tails.",
            "vocal": "Silky lead vocal with modern runs and airy falsetto, intimate and close-miked, layered with soft doubled harmonies and occasional breathy ad-libs.",
            "arrangement": "Trap-influenced slow beat with rolling hi-hats, deep 808 sub bass, glossy electric piano and pads. Intro: filtered chords and a vocal ad-lib. Verses: sparse beat with keys and vocal. Chorus: fuller pads and stacked harmonies. Bridge: beat thins to pads and vocals. Outro: vocal runs dissolve into reverb.",
        },
        "放克 / Funk": {
            "global": "Funk. Groovy, syncopated, and full of swagger throughout, a hot Saturday-night dance floor. Sweaty clubs, mirrored balls, infectious energy. Punchy analog production: tight snappy drums, clean guitar stabs, fat analog synths.",
            "vocal": "Charismatic call-and-response vocal with short rhythmic phrases, shouts, and playful ad-libs, sitting right on top of the groove.",
            "arrangement": "Tight four-on-the-floor drums with a cracking snare, slapping electric bass locked to the kick, rhythmic wah-wah guitar stabs, bright horn section hits. Intro: drums and bass build the groove. Verses: sparse groove with vocal. Chorus: full band with horn punches. Breakdown: rhythm section only, call-and-response. Outro: a final horn hit and stop.",
        },
        "嘻哈 / Hip-Hop": {
            "global": "Hard-hitting hip-hop. Confident, gritty, and rhythmic throughout, a late-night block-party energy. Street corners, car bass, raw momentum. Punchy production: heavy 808 bass, crisp trap snares, dark minor-key loops.",
            "vocal": "Confident rap vocal with sharp rhythmic flow, tight double-time passages, and hard-hitting punchlines, delivered with swagger and occasional ad-libs.",
            "arrangement": "Heavy 808-driven beat with rolling hi-hats, snapping snares, dark piano or synth loop. Intro: filtered loop and a vocal tag. Verses: full rap delivery over the beat. Chorus: anthemic hook with layered vocals. Bridge: beat drops to bass and hi-hats. Outro: the loop fades with a final ad-lib.",
        },
        "电子 / Electronic": {
            "global": "Electronic. Pulsing, hypnotic, and atmospheric throughout, a neon-lit night drive. Synth textures, glowing pads, rhythmic momentum. Clean digital production: wide stereo field, precise transients, deep sub bass.",
            "vocal": "Processed, reverb-soaked vocal fragments floating through the mix, treated as texture with heavy delay and subtle pitch modulation, never leading the track.",
            "arrangement": "Four-on-the-floor kick, layered synth arpeggios, pulsing bassline, airy pads and arpeggiated plucks. Intro: filtered pads build. Build-up: risers and snare rolls raise tension. Drop: full groove with driving bass. Breakdown: pads and vocal fragments. Outro: elements filter away one by one.",
        },
        "氛围 / Ambient": {
            "global": "Ambient. Spacious, weightless, and slowly evolving throughout, a vast drift through soft clouds. Floating in stillness, deep breathing, quiet introspection. Clean production: long reverb tails, no percussion, soft dynamic swells.",
            "vocal": "No vocals — only airy, wordless hums and distant choir-like pads that bloom and fade like light.",
            "arrangement": "Slow-moving pad swells, gentle piano notes with long decay, soft field recordings of wind and distant water. Opening: a single drone rises. Middle: layers of pads breathe in and out. Closing: everything dissolves into a single lingering harmonic.",
        },
        "合成器浪潮 / Synthwave": {
            "global": "Synthwave. Retro-futuristic, neon-drenched, and cinematic throughout, a night drive through a glowing 1980s city. Chrome, neon signs, rain-slicked streets. Vintage synth production: analog warmth, gated reverb, tape saturation.",
            "vocal": "Sparse, filtered female vocal with heavy chorus and delay, delivered in detached melodic phrases like a distant radio transmission.",
            "arrangement": "Driving drum machine beat, pulsing analog bassline, shimmering arpeggios, wide pads. Intro: pads and a rising arp. Verses: bass and drums lock in with vocal. Chorus: anthemic synth lead over the full groove. Bridge: everything thins to a pad. Outro: arps fade into neon haze.",
        },
        "芯片音乐 / Chiptune": {
            "global": "Chiptune. Bright, bouncy, and nostalgic throughout, an 8-bit arcade adventure. Retro game-console energy, pixel skies, heroic optimism. Authentic chip production: square-wave leads, triangle bass, noise-channel drums.",
            "vocal": "No vocals — melodies are carried by bright square-wave leads that sing like game themes.",
            "arrangement": "Square-wave lead melody, triangle-wave bassline, pulse-width modulation chords, noise-channel hi-hats and snare. Intro: title-screen fanfare. Main theme: bouncy melody over bass. Breakdown: melody thins to bass and noise. Outro: the final note holds and fades.",
        },
        "浩室 / House": {
            "global": "House. Deep, groovy, and uplifting throughout, a late-night warehouse pulse. Four-on-the-floor heartbeat, sweaty dance floor, hands in the air. Punchy production: deep kick, swinging percussion, warm chords.",
            "vocal": "Soulful vocal hooks sampled and chopped, repeated hypnotically with delay, short gospel-tinged phrases that lift the groove.",
            "arrangement": "Driving four-on-the-floor kick, swinging hi-hats and claps, warm chord stabs, rolling bassline. Intro: filtered chords and percussion build. Drop: full groove with vocal hook. Breakdown: chords and vocal alone. Build-up: risers and snare rolls. Final drop: everything returns fuller. Outro: groove strips to a kick.",
        },
        "科技舞曲 / Techno": {
            "global": "Techno. Dark, hypnotic, and relentless throughout, a cavernous warehouse at 4 a.m. Industrial textures, strobe light, driving momentum. Raw production: pounding kick, metallic percussion, reverb-drenched atmosphere.",
            "vocal": "Minimal vocals — only sparse, heavily processed spoken fragments and distant industrial whispers used as rhythmic texture.",
            "arrangement": "Pounding kick drum, rolling bassline, metallic hats, clattering percussion, eerie stabs. Intro: percussion layers build. Core: relentless groove with evolving textures. Breakdown: kick drops to a drone. Build-up: tension rises with hats. Final: groove returns harder. Outro: elements strip away to the kick.",
        },
        "鼓打贝斯 / Drum & Bass": {
            "global": "Drum & bass. Fast, high-energy, and intricate throughout, a midnight rave at full speed. Breakneck rhythms, rolling bass, adrenaline rush. Precise production: tight breaks, deep sub bass, crisp transients.",
            "vocal": "Soulful female vocal phrases floating above the chaos, pitched and chopped, offering brief melodic respites between drops.",
            "arrangement": "Amen-style breakbeats at 170+ BPM, deep wobbling sub bass, atmospheric pads, syncopated stabs. Intro: pads and vocals. Build-up: rising riser and break fills. Drop: full-speed drums and bass. Breakdown: pads and vocal. Second drop: heavier bassline. Outro: drums cut to a final sub hit.",
        },
        "摇滚 / Rock": {
            "global": "Rock. Gritty, driving, and full of attitude throughout, a sweaty club show. Distorted guitars, pounding drums, raw energy. Punchy production: crunchy guitars, tight drums, slightly overdriven mix.",
            "vocal": "Raspy, powerful male vocal delivered with grit and range, rising from a growl in the verses to a soaring belt in the chorus.",
            "arrangement": "Driving drums, distorted power-chord guitars, pulsing bass, anthemic lead riffs. Intro: guitar riff kicks in. Verses: vocal over driving chords. Chorus: full band at maximum, soaring vocal. Guitar solo: melodic and fiery. Bridge: dynamics drop then rebuild. Outro: a final chord rings out.",
        },
        "独立民谣 / Indie Folk": {
            "global": "Indie folk. Tender, organic, and intimate throughout, a cabin in the woods at golden hour. Campfire warmth, falling leaves, quiet storytelling. Warm acoustic production: close-miked instruments, natural room ambience, soft tape warmth.",
            "vocal": "Gentle, confessional vocal with a slight rasp, sung close to the mic with honest, unadorned phrasing and soft harmonies in the chorus.",
            "arrangement": "Fingerpicked acoustic guitar, soft banjo and mandolin accents, upright bass, light brushed percussion. Intro: solo guitar melody. Verses: voice and guitar, sparse. Chorus: harmonies and light percussion swell. Bridge: strings drift in. Outro: a final guitar note rings over silence.",
        },
        "原声吉他 / Acoustic": {
            "global": "Solo acoustic guitar. Warm, intimate, and unhurried throughout, a quiet morning by the window. Coffee steam, soft sunlight, peaceful stillness. Natural production: close-miked with warm room tone, no effects beyond gentle reverb.",
            "vocal": "No vocals — the guitar alone carries every melody and emotion.",
            "arrangement": "Fingerpicked arpeggios and gentle strumming, with a soft melody line woven through the chords. Opening: a slow picking pattern establishes the mood. Middle: the melody rises and falls. Closing: the final chord decays into silence.",
        },
        "钢琴 / Piano": {
            "global": "Solo piano. Delicate, expressive, and introspective throughout, a quiet candlelit room. Rain on glass, slow thoughts, gentle melancholy. Natural production: warm close-miked piano, soft pedal noise, natural decay.",
            "vocal": "No vocals — the piano alone sings every phrase.",
            "arrangement": "Sparse left-hand chords under a singing right-hand melody, with gentle rubato and long pauses. Opening: a simple motif. Middle: the motif develops and swells. Closing: the opening theme returns, softer, ending on an unresolved chord.",
        },
        "管弦乐 / Orchestral": {
            "global": "Full orchestra. Grand, sweeping, and cinematic throughout, a vast score for an epic story. Concert-hall acoustics, soaring strings, majestic brass. Rich production: wide dynamic range, natural hall reverb, detailed sections.",
            "vocal": "No solo vocals — an optional wordless choir rises in the climax like a distant heavenly voice.",
            "arrangement": "Sweeping string melodies, warm French horn chorales, woodwind colors, timpani and cymbal accents. Opening: soft strings establish a theme. Build: brass and percussion swell. Climax: full orchestra at maximum. Denouement: strings alone. Ending: a final quiet chord.",
        },
        "史诗 / Epic": {
            "global": "Epic cinematic score. Powerful, heroic, and larger than life throughout, a battle cry on a grand scale. Thundering drums, soaring choirs, world-shaking intensity. Huge production: massive percussion, wall-of-sound strings, dramatic swells.",
            "vocal": "Powerful wordless choir chanting over the climax, layered male and female voices rising like an army's anthem.",
            "arrangement": "Thundering taiko drums, relentless string ostinatos, blaring brass fanfares, choir swells. Opening: low strings and drums build. Rises: tension climbs step by step. Climax: full choir and orchestra explode. Aftermath: strings fade. Ending: a final drum hit and silence.",
        },
        "浪漫弦乐 / Romantic Strings": {
            "global": "Romantic strings. Lush, tender, and sweeping throughout, a candlelit waltz under starlight. Slow dances, soft embraces, timeless elegance. Rich production: warm vibrato, soaring legato lines, gentle hall reverb.",
            "vocal": "No vocals — the strings themselves sing the melody with aching lyricism.",
            "arrangement": "Lush violin melody over warm cello and viola harmonies, with harp glissandos and delicate pizzicato. Opening: cello introduces a theme. Middle: violins soar in unison. Swell: full section in passionate vibrato. Ending: the melody dissolves into a single held note.",
        },
        "悬疑 / Suspense": {
            "global": "Suspenseful thriller score. Tense, creeping, and unsettling throughout, a shadow moving at the edge of sight. Dark corridors, held breath, quiet dread. Detailed production: close-miked textures, deep drones, sudden silences.",
            "vocal": "No vocals — only eerie, wordless whispers and distant humming used as texture.",
            "arrangement": "Low-frequency drones, sparse piano notes, ticking percussion, dissonant string clusters. Opening: a low drone and a heartbeat pulse. Build: textures layer and tighten. Stabs: sudden dissonant hits. Release: silence, then a whisper. Ending: an unresolved note hangs.",
        },
        "国风民乐 / Chinese Folk": {
            "global": "Traditional Chinese folk music. Graceful, poetic, and evocative throughout, a misty mountain landscape at dawn. Ink-wash scenery, flowing rivers, ancient villages. Natural production: close-miked instruments, gentle room ambience, unhurried phrasing.",
            "vocal": "Ethereal female vocal with soft vibrato, singing a pentatonic melody like a distant mountain song, occasionally humming wordlessly.",
            "arrangement": "Guzheng glissandos, erhu melodic lines, dizi bamboo flute trills, pipa tremolos. Opening: guzheng sets a flowing texture. Theme: erhu and flute trade phrases. Middle: pipa adds rhythmic color. Ending: flute fades over a guzheng echo.",
        },
        "古琴 / Guqin": {
            "global": "Solo guqin. Deep, meditative, and profoundly still throughout, a scholar's study in moonlight. Incense smoke, still water, ancient wisdom. Natural production: intimate close-miking, every string texture and finger slide audible.",
            "vocal": "No vocals — only the guqin's resonant strings and occasional soft harmonic overtones.",
            "arrangement": "Slow, sparse plucked phrases with long silences between notes, subtle slides and harmonics. Opening: a single deep note. Middle: phrases unfold like breath. Closing: harmonics fade into silence.",
        },
        "戏曲 / Chinese Opera": {
            "global": "Stylized Chinese opera. Dramatic, theatrical, and intensely expressive throughout, a stage of painted faces and flowing robes. Gongs and clappers, piercing falsetto, ancient drama. Traditional production: live stage acoustics, bright percussion, unprocessed vocals.",
            "vocal": "Piercing theatrical vocal in traditional opera style, alternating between dramatic declamation and high falsetto, ornamented with vibrato and slides.",
            "arrangement": "Clanging gongs, wooden clappers, piercing erhu, bamboo flute. Opening: gong and clappers announce. Recitation: vocal declaims over sparse percussion. Aria: full band with expressive vocal. Climax: gongs crash. Ending: a final clap and silence.",
        },
        "冥想 / Meditation": {
            "global": "Meditative soundscape. Calm, grounding, and deeply peaceful throughout, a still morning beside a temple. Slow breathing, soft light, inner quiet. Pure production: long tones, no sharp transients, gentle swells.",
            "vocal": "Soft wordless humming and long vowel tones, like a gentle chant, floating above the drones.",
            "arrangement": "Singing bowls, slow drone pads, soft wind chimes, distant flute. Opening: a singing bowl rings. Middle: drones and bowls layer softly. Closing: everything fades to a single pure tone.",
        },
        "自然白噪音 / Nature Ambient": {
            "global": "Nature ambience. Organic, soothing, and immersive throughout, a rainforest at dawn. Rain on leaves, distant birds, flowing streams. Field-recording production: untouched natural textures, gentle spatial depth, no melody.",
            "vocal": "No vocals — only birdsong and wind carry the soundscape.",
            "arrangement": "Layered field recordings of rain, wind through trees, distant thunder, birdsong and crickets. Opening: rain fades in. Middle: birds and wind join. Closing: rain alone, fading softly.",
        },
        # ── 官方 genre-router 家族补充 ──
        "华语流行 / Mandopop": {
            "global": "Mandopop, contemporary Chinese pop. Melodic, heartfelt, and polished throughout, a warm city-pop glow with modern production sheen. Late-night drives, city lights, youthful longing. Clean modern production: bright keys, glossy synths, tight punchy mix with a subtle electronic flavor.",
            "vocal": "Warm, expressive Chinese vocal with clear diction and gentle vibrato, emotional phrasing that rises from intimate verses into an open, soaring chorus, with soft doubled harmonies and airy backing layers.",
            "arrangement": "Mid-tempo pop beat with crisp drums and a round bassline, warm electric piano and glossy synth pads, subtle guitar arpeggios. Intro: filtered keys and a soft vocal breath. Verses: minimal beat with keys and vocal. Pre-chorus: tension builds with rising pads. Chorus: full band, soaring vocal, stacked harmonies. Bridge: everything thins to piano and voice. Outro: the hook fades over a final chord.",
        },
        "国风流行 / Guofeng Pop": {
            "global": "Guofeng pop, a Chinese-style pop ballad blending traditional and modern elements. Poetic, graceful, and deeply evocative throughout, ink-wash imagery and ancient longing. Moonlit pavilions, falling blossoms, flowing robes. Hybrid production: traditional Chinese instruments woven into a modern ballad mix.",
            "vocal": "Ethereal, emotive vocal with soft vibrato and delicate ornamentation, delivered in a flowing legato style with occasional airy falsetto and gentle layered harmonies.",
            "arrangement": "Piano and guzheng share the harmonic bed, with erhu melodic lines, dizi flute accents, and subtle electronic pads over a slow pop beat. Intro: guzheng glissando over piano. Verses: sparse piano and vocal with guzheng echoes. Chorus: drums enter with strings and dizi, vocal soars. Bridge: erhu solo over pads. Outro: a single guzheng note fades.",
        },
        "流行 / Pop": {
            "global": "Contemporary pop. Bright, catchy, and universally appealing throughout, a polished radio-ready sound. Hooks, tight production, wide appeal. Clean modern production: crisp drums, deep bass, glossy synths, shimmering top end.",
            "vocal": "Clear, confident lead vocal with a bright, radio-friendly tone, strong hook delivery, layered harmonies and ad-libs, subtly pitch-polished.",
            "arrangement": "Upbeat pop beat, punchy bass, sparkling synths, rhythmic guitar, anthemic hooks. Intro: hooky instrumental riff. Verses: sparse beat with vocal. Pre-chorus: tension builds. Chorus: massive hook with stacked harmonies. Bridge: stripped-back moment. Final chorus: everything returns bigger. Outro: the hook fades out.",
        },
        "金属 / Metal": {
            "global": "Metal. Heavy and aggressive throughout, a wall of distorted guitars and thunderous drums. Raw intensity, chugging riffs, visceral power. Punchy production: heavily distorted guitars, tight double-kick drums, roaring low end.",
            "vocal": "Harsh, powerful vocal alternating between a guttural growl and a soaring melodic clean chorus, delivered with maximum intensity and occasional gang shouts.",
            "arrangement": "Driving double-kick drums, palm-muted chugging riffs, screaming lead guitar, roaring bass. Intro: a fast riff and drum fill kick in. Verses: chugging guitars under growled vocals. Chorus: melodic clean vocal over soaring chords. Breakdown: half-time heaviness. Guitar solo: fast and technical. Outro: a final chug ends abruptly.",
        },
        "布鲁斯 / Blues": {
            "global": "Traditional blues. Gritty, soulful, and deeply felt throughout, a smoky back-room juke joint. Slow-burning twelve-bar changes, call-and-response, raw honesty. Vintage production: warm tube amps, room ambience, unpolished and honest.",
            "vocal": "Weathered, gravelly vocal with bent notes and heartfelt phrasing, alternating between a spoken growl and a full-throated wail, full of call-and-response character.",
            "arrangement": "Twelve-bar blues progression with a walking bass, shuffle drums, rhythmic rhythm guitar, and expressive lead guitar fills. Intro: a slow bluesy guitar riff. Verses: vocal over the shuffle with guitar answers. Solos: smoky, bluesy guitar and harmonica trade phrases. Outro: the band winds down to a final bent note.",
        },
        "乡村 / Country": {
            "global": "Country. Warm and down-to-earth throughout, a dusty backroad at sunset. Storytelling, pedal steel, honest roots. Warm production: close-miked acoustic instruments, natural room ambience, gentle twang.",
            "vocal": "Warm, twangy vocal with sincere, storytelling delivery and a slight southern drawl, joined by tight close harmonies on the chorus.",
            "arrangement": "Acoustic and electric guitars, pedal steel swells, fiddle accents, upright bass, brushed snare. Intro: acoustic guitar and pedal steel. Verses: vocal over strumming. Chorus: full band with harmonies and fiddle. Bridge: pedal steel solo. Outro: guitar and steel fade together.",
        },
        "摇摆爵士 / Swing & Big Band": {
            "global": "Big band swing. Bouncy, brassy, and exuberant throughout, a 1940s dance hall in full swing. Tight horn sections, swinging rhythm, vintage glamour. Authentic production: bright brass, natural room reverb, vintage mono warmth.",
            "vocal": "Charismatic crooner vocal with a warm, rounded tone and effortless swing phrasing, occasionally joined by playful scat syllables and call-and-response with the band.",
            "arrangement": "Tight brass section with trumpets, trombones, and saxophones, swinging rhythm guitar, walking bass, and crisp hi-hat drums. Intro: full band hits a swinging riff. Head: vocal over the swing. Solos: trumpet, sax, and trombone trade phrases. Final chorus: shout chorus with the full band. Outro: a final brass stab.",
        },
        "迪斯科 / Disco": {
            "global": "Disco. Glittering, euphoric, and endlessly danceable throughout, a mirrored dance floor under a spinning ball. Four-on-the-floor pulse, lush strings, funky bass. Shimmering production: sparkling strings, punchy drums, wide dance-floor mix.",
            "vocal": "Smooth, soaring vocal with rich harmonies and falsetto lifts, delivered with disco flair and echoed call-and-response phrases.",
            "arrangement": "Four-on-the-floor kick, walking octave bass, wah-wah rhythm guitar, lush string section, bright horns. Intro: strings and bass build. Verses: vocal over the pulse. Chorus: full band with strings and harmonies. Breakdown: percussion and bass. Final chorus: everything returns bigger. Outro: a final string hit.",
        },
        "出神 / Trance": {
            "global": "Trance. Uplifting, euphoric, and hypnotic throughout, a vast festival mainstage at night. Sweeping supersaws, rolling bass, hands-in-the-air breakdowns. Huge production: wide supersaw stacks, driving fast kick, epic reverb-drenched builds.",
            "vocal": "Ethereal female vocal floating above the mix with reverb-drenched phrases and airy harmonies, providing brief melodic hooks between the drops.",
            "arrangement": "Driving four-on-the-floor kick, rolling bassline, shimmering arpeggios, sweeping supersaw pads. Intro: pads and arps build. Breakdown: vocal and pads with a long build. Drop: full supersaw wall of sound. Second breakdown: emotional piano and vocal. Final drop: everything returns euphoric. Outro: pads fade into silence.",
        },
        "雷鬼 / Reggae": {
            "global": "Reggae. Laid-back, rhythmic, and sun-soaked throughout, an island afternoon sway. Offbeat skank guitar, deep bass, irie vibrations. Warm production: analog warmth, deep sub bass, laid-back groove.",
            "vocal": "Relaxed, soulful vocal with a melodic, conversational delivery, singing with warmth and occasional harmony backing, easy and unhurried.",
            "arrangement": "Offbeat skank guitar, deep round bassline, one-drop drums with rimshot accents, bright organ stabs. Intro: bass and skank set the groove. Verses: vocal floats over the one-drop. Chorus: harmonies lift. Instrumental: melodica or guitar solo. Outro: groove fades into dub echo.",
        },
        "福音 / Gospel": {
            "global": "Gospel. Soulful, uplifting, and deeply spiritual throughout, a swaying church choir raised in joyful praise. Handclaps, hammond organ, soaring harmonies. Warm live production: natural room reverb, rich choir, organic and reverent.",
            "vocal": "Powerful lead vocal with gospel runs and call-and-response, backed by a lush choir with tight four-part harmonies, alternating between solo verses and full-chorus swells.",
            "arrangement": "Hammond organ swells, rhythmic handclaps, walking bass, piano and a full choir. Intro: organ and a solo vocal line. Verses: call-and-response between lead and choir. Chorus: full choir in stacked harmonies with handclaps. Bridge: everything drops to organ and a cappella voices. Outro: a final soaring vocal run fading into a held chord.",
        },
        "阿卡贝拉 / A Cappella": {
            "global": "A cappella. Pure vocal, no instruments, intimate and expressive throughout. Layered human voices, close harmonies, vocal bass and beatbox percussion. Clean production: close-miked voices, natural ambience, crisp vocal clarity.",
            "vocal": "Layered vocal arrangement with a clear lead voice, tight four-part harmonies, and vocal bass or beatbox percussion, all human voices with no instruments.",
            "arrangement": "All vocals: lead melody, close harmonies, vocal bass line, and mouth-percussion. Intro: a vocal bass groove. Verses: lead voice over harmony pads. Chorus: full vocal stack in rich harmony. Breakdown: solo voice and beatbox. Outro: voices fade one by one into a final held chord.",
        },
    }

    # 官方 genre-router 18 家族未覆盖、节点额外补充的风格（其余均标 [官方]）
    _SUPPLEMENT_STYLES = {
        "芯片音乐 / Chiptune",
        "冥想 / Meditation",
        "自然白噪音 / Nature Ambient",
    }

    # ═══════════════════════════════════════════════════════════
    #  可选维度 hint（值为英文短句，拼进 Global Metadata / Vocal Details）
    # ═══════════════════════════════════════════════════════════

    _BPM_HINTS = {
        "不指定 / Unspecified": "",
        "慢速 60-75 / Slow 60-75 BPM": "60-75 BPM",
        "中速 80-100 / Mid 80-100 BPM": "80-100 BPM",
        "中快 100-110 / Mid-Fast 100-110 BPM": "100-110 BPM",
        "快速 110-135 / Fast 110-135 BPM": "110-135 BPM",
        "极快 140+ / Very Fast 140+ BPM": "140+ BPM",
    }

    _KEY_HINTS = {
        "不指定 / Unspecified": "",
        "C / C": "C",
        "降D / D-flat": "D-flat",
        "D / D": "D",
        "降E / E-flat": "E-flat",
        "E / E": "E",
        "F / F": "F",
        "升F / F-sharp": "F-sharp",
        "G / G": "G",
        "降A / A-flat": "A-flat",
        "A / A": "A",
        "降B / B-flat": "B-flat",
        "B / B": "B",
    }

    _SCALE_HINTS = {
        "不指定 / Unspecified": "",
        # 自然大/小调
        "大调 / Major": "major",
        "小调 / Minor": "minor",
        # 和声/旋律变体
        "和声小调 / Harmonic Minor": "harmonic minor",
        "旋律小调 / Melodic Minor": "melodic minor",
        "和声大调 / Harmonic Major": "harmonic major",
        # 教会调式
        "多利亚 / Dorian": "Dorian",
        "弗里吉亚 / Phrygian": "Phrygian",
        "利底亚 / Lydian": "Lydian",
        "混合利底亚 / Mixolydian": "Mixolydian",
        "洛克里亚 / Locrian": "Locrian",
        # 五声/布鲁斯
        "大调五声 / Major Pentatonic": "major pentatonic",
        "小调五声 / Minor Pentatonic": "minor pentatonic",
        "布鲁斯 / Blues Scale": "blues scale",
        # 其他
        "中国五声 / Chinese Pentatonic": "Chinese pentatonic",
        "爵士扩展 / Jazzy Extensions": "major scale with jazzy extensions",
    }

    # 只选调式不选调号时，把裸调式名补成完整短语
    _BARE_SCALE_PHRASES = {
        "major": "major key",
        "minor": "minor key",
        "harmonic minor": "harmonic minor scale",
        "melodic minor": "melodic minor scale",
        "harmonic major": "harmonic major scale",
        "Dorian": "Dorian mode",
        "Phrygian": "Phrygian mode",
        "Lydian": "Lydian mode",
        "Mixolydian": "Mixolydian mode",
        "Locrian": "Locrian mode",
        "major pentatonic": "major pentatonic scale",
        "minor pentatonic": "minor pentatonic scale",
        "Chinese pentatonic": "Chinese pentatonic scale",
    }

    _MOOD_HINTS = {
        "不指定 / Unspecified": "",
        "梦幻 / Dreamy": "Dreamy and ethereal",
        "放松 / Laid-back": "Laid-back and relaxed",
        "温暖 / Warm": "Warm and comforting",
        "忧郁 / Melancholic": "Melancholic and wistful",
        "高能 / Energetic": "Energetic and driving",
        "紧张 / Tense": "Tense and suspenseful",
        "神秘 / Mysterious": "Mysterious and haunting",
        "神圣 / Ethereal": "Ethereal and celestial",
        "浪漫 / Romantic": "Romantic and tender",
        "悲伤 / Sad": "Sad and sorrowful",
        "希望 / Hopeful": "Hopeful and uplifting",
        "迷幻 / Psychedelic": "Psychedelic and trippy",
        "庄严 / Solemn": "Solemn and reverent",
        "怀旧 / Nostalgic": "Nostalgic and bittersweet",
        "欢庆 / Celebratory": "Celebratory and jubilant",
        "治愈 / Healing": "Healing and comforting",
        "欣快 / Euphoric": "Euphoric and cathartic",
    }

    _SCENE_HINTS = {
        "不指定 / Unspecified": "",
        "学习 / Studying": "Studying",
        "雨夜 / Raining Outside": "Raining outside",
        "深夜耳机 / Late-night Headphones": "Headphones-on late-night listening",
        "驾驶 / Driving": "Night driving",
        "健身 / Workout": "Workout",
        "冥想 / Meditation": "Meditation and deep focus",
        "咖啡店 / Coffee Shop": "Cozy coffee shop",
        "睡前 / Bedtime": "Winding down before bed",
        "派对 / Party": "Party",
        "游戏 / Gaming": "Gaming",
        "通勤 / Commute": "Commuting",
        "温泉 / Spa": "Spa and relaxation",
        "晨间 / Morning": "Morning",
        "黄昏 / Sunset": "Golden-hour sunset",
        "跑步 / Running": "Running",
    }

    # 人声拆为三个轴：配置(性别) / 音色 / 唱法，自由组合；和声单独控制
    _VOCAL_CONFIG_HINTS = {
        "跟随风格 / Follow Style": "",
        "无人声 / Instrumental (No Vocals)": "No vocals at all — a pure instrumental arrangement, every melody carried by instruments.",
        "女声 / Female Vocal": "female vocal",
        "男声 / Male Vocal": "male vocal",
        "童声 / Child Vocal": "child's voice",
        "柔和中性 / Soft Androgynous Vocal": "soft androgynous vocal",
        "合唱 / Choir": "large mixed SATB choir (sopranos, altos, tenors, basses)",
        "纯人声 / Acappella (Vocals Only)": "a pure acappella vocal performance with no instrumental accompaniment",
    }

    _REGISTER_HINTS = {
        "跟随风格 / Follow Style": "",
        "女高音 / Soprano": "soprano",
        "女中音 / Mezzo-Soprano": "mezzo-soprano",
        "女低音 / Alto": "alto",
        "男高音 / Tenor": "tenor",
        "男中音 / Baritone": "baritone",
        "男中高音 / Baritenor": "baritenor",
        "男低音 / Bass": "bass",
    }

    _VOCAL_TIMBRE_HINTS = {
        "跟随风格 / Follow Style": "",
        "清亮 / Clear Bright": "clear, bright",
        "温暖 / Warm": "warm",
        "烟嗓 / Smoky Husky": "smoky, husky",
        "沧桑 / Weathered Gravelly": "weathered, gravelly",
        "气声 / Breathy": "breathy",
        "空灵 / Ethereal Airy": "ethereal, airy",
        "浑厚 / Deep Rich": "deep, rich",
        "磁性 / Magnetic": "magnetic, rich",
        "慵懒 / Lazy Laid-Back": "lazy, laid-back",
        "纯净 / Pure Clean": "pure, clean",
        "丝绒 / Velvety": "velvety, smooth",
        "蜜糖 / Honeyed": "honeyed, warm",
    }

    _VOCAL_STYLE_HINTS = {
        "跟随风格 / Follow Style": "",
        "假声 / Falsetto": "falsetto delivery",
        "半说半唱 / Half-Sung Half-Spoken": "half-sung half-spoken delivery",
        "说唱 / Rap Flow": "rap flow",
        "呼麦 / Throat Singing": "throat singing (khoomei)",
        "民谣 / Folk Storytelling": "folk storytelling delivery",
        "美声 / Bel Canto": "operatic bel canto delivery",
        "流行/通俗 / Pop Vocal": "pop vocal delivery",
        "民族唱法 / Chinese Folk Singing": "Chinese folk-style singing technique",
        "颤音 / Vibrato": "expressive vibrato",
        "断奏 / Staccato": "staccato phrasing",
        "戏腔 / Chinese Opera Style": "Chinese opera-style delivery with ornamented vibrato and slides",
        "吟唱 / Chant": "chant-like, repetitive phrasing",
        "约德尔 / Yodeling": "yodeling with rapid register breaks",
        "嘶吼 / Growl": "guttural growl",
    }

    _HARMONY_HINTS = {
        "跟随风格 / Follow Style": "",
        "无和声 / No Harmony": "no harmony",
        "双声部和声 / Double-Tracked Harmonies": "tight double-tracked harmonies",
        "多人叠唱 / Stacked Harmonies": "stacked multi-voice harmonies",
        "伴唱垫底 / Backing Vocals": "soft backing vocals underneath",
    }

    _VOCAL_FX_HINTS = {
        "跟随风格 / Follow Style": "",
        "磁带延迟 / Tape Delay": "drenched in tape delay and warm spring reverb",
        "暖混响 / Warm Reverb": "drenched in warm plate reverb",
        "自动调音 / Auto-Tune": "subtle Auto-Tune polish with a modern sheen",
        "干声无效果 / Dry (No FX)": "dry, close-miked vocal with no audible effects",
        "回声 / Echo": "spacious echo and gentle slap-back delay",
    }

    # ═══════════════════════════════════════════════════════════
    #  合唱团（官方合唱范式）
    #  官方模板 cinematic-orchestral-epic-choral 把合唱团声明写在
    #  「Vocal Gender & Timbre」子块，SATB 编配细节写在「Harmony/Backing
    #  Vocals」子块；gt 字段不带冠词，由 _art() 动态补 a / an。
    # ═══════════════════════════════════════════════════════════
    _CHOIR_HINTS = {
        "无 / None": {"gt": "", "choir_line": "", "harm": ""},
        "小型和声组 / Small Backing Group": {
            "gt": "small backing vocal group of three to four singers",
            "choir_line": "The backing group stays tight and tucked behind the lead, adding weight without taking focus",
            "harm": "A small backing vocal group answers the lead in unison and simple two-part harmony, thickening the choruses",
        },
        "大型混声合唱团 / Large Mixed SATB Choir": {
            "gt": "large mixed SATB choir (sopranos, altos, tenors, basses)",
            "choir_line": "The choir provides a massive, unified wall of sound, ranging from deep, rumbling basses to ethereal, high-register sopranos",
            "harm": "Rich, four-part SATB arrangements double the melodic lines an octave apart and provide counter-melodies, creating a wall-of-sound effect",
        },
        "童声合唱团 / Children's Choir": {
            "gt": "children's choir of bright, pure voices",
            "choir_line": "The children's choir sits high and clear above the lead, its untrained purity sharpening the emotional edge",
            "harm": "A children's choir adds bright unison and two-part harmonies above the lead",
        },
        "福音合唱团 / Gospel Choir": {
            "gt": "full gospel choir with powerful, soulful mixed voices",
            "choir_line": "The gospel choir swells behind the lead with impassioned shouts and rich four-part harmony",
            "harm": "A gospel choir answers the lead with call-and-response shouts and rich four-part harmony, surging through the choruses",
        },
    }

    _TEXTURE_HINTS = {
        "跟随风格 / Follow Style": "",
        "干净数字 / Clean Digital": "Clean digital production: crisp highs, tight low end, polished mix with no noise or lo-fi artifacts.",
        "温暖模拟 / Warm Analog": "Warm analog production: soft saturation, gentle tube warmth, slightly rounded transients.",
        "磁带 Lo-fi / Tape Lo-fi": "Tape lo-fi production: heavy tape hiss, wow-and-flutter pitch wobble, low-passed dusty mix, everything slightly detuned and cozy.",
        "黑胶噪点 / Vinyl Crackle": "Vinyl production: constant crackle and surface noise, warm low end, vintage EQ curve.",
        "宽广开阔 / Wide Spacious": "a wide, spacious mix with an expansive stereo image",
        "大厅混响 / Hall Reverb": "a mix drenched in natural hall reverb",
        "现场房间 / Live Room": "a natural live-room sound with realistic space",
    }

    _METER_HINTS = {
        "不指定 / Unspecified": "",
        "4/4": "4/4 time",
        "3/4": "3/4 waltz time",
        "6/8": "6/8 time",
        "12/8": "12/8 shuffle",
        "2/4": "2/4 time",
        "5/4": "5/4 time",
        "7/8": "7/8 time",
    }

    _CONTOUR_HINTS = {
        "不指定 / Unspecified": "",
        # 渐变型：能量单调上行/下行
        "由静到扬 / Gradual Rise": "a gradual emotional rise that opens calm and builds steadily into an uplifting peak",
        "由扬到静 / Gradual Fade": "a gradual emotional fade that opens energetic and steadily settles into a calm close",
        # 反转型：有明显的「抑↔扬」转折对比
        "先抑后扬 / Suppressed→Erupt": "a reversal arc that holds the mood low and restrained, then erupts into a climactic release",
        "先扬后抑 / Peak→Dissolve": "a reversal arc that opens at an emotional peak, then falls and dissolves into quiet",
        # 平稳型：情绪恒定
        "持续平静 / Steady Calm": "a steady, even emotional contour that stays calm and unhurried throughout",
        "持续高能 / Steady Energetic": "a steady, high-energy emotional contour that stays intense and driving throughout",
        # 复合型：多次起伏
        "起承转合 / Rise-Fall-Rise": "a classic rise-fall-rise emotional arc with tension building, releasing, and building again",
        "跌宕起伏 / Rollercoaster": "repeated dramatic swings between tension and release, with multiple emotional peaks and valleys",
    }

    _STRUCTURE_HINTS = {
        "跟随风格 / Follow Style": "",
        "标准流行 / Standard Pop": "Song structure: Intro → Verse → Pre-Chorus → Chorus → Verse → Chorus → Bridge → Final Chorus → Outro",
        "简洁 / Compact": "Song structure: Verse → Chorus → Verse → Chorus → Outro",
        "无 Intro / No Intro": "Song structure: Verse → Pre-Chorus → Chorus → Verse → Chorus → Bridge → Outro",
        "含器乐间奏 / With Instrumental Break": "with an instrumental break between the second chorus and the bridge",
        "含 Breakdown / With Breakdown": "with a stripped-down breakdown before the final chorus",
    }

    # 官方 Arrangement 支持指定 primary / secondary instruments
    _INSTRUMENT_HINTS = {
        # 键盘
        "钢琴 / Piano": "piano",
        "电钢琴 / Electric Piano": "electric piano",
        "管风琴 / Organ": "organ",
        "合成器 / Synthesizer": "synthesizer",
        # 弦乐
        "小提琴 / Violin": "violin",
        "中提琴 / Viola": "viola",
        "大提琴 / Cello": "cello",
        "弦乐组 / Strings": "strings",
        "竖琴 / Harp": "harp",
        # 木管
        "长笛 / Flute": "flute",
        "单簧管 / Clarinet": "clarinet",
        "双簧管 / Oboe": "oboe",
        "萨克斯 / Saxophone": "saxophone",
        # 铜管
        "小号 / Trumpet": "trumpet",
        "长号 / Trombone": "trombone",
        "法国号 / French Horn": "French horn",
        # 吉他/贝斯
        "原声吉他 / Acoustic Guitar": "acoustic guitar",
        "电吉他 / Electric Guitar": "electric guitar",
        "贝斯 / Bass": "bass",
        # 打击
        "鼓 / Drums": "drums",
        "打击乐 / Percussion": "percussion",
        # 中国民族
        "古筝 / Guzheng": "guzheng",
        "古琴 / Guqin": "guqin",
        "笛子 / Dizi": "dizi",
    }

    # ═══════════════════════════════════════════════════════════
    #  一键配方（新手「完美配方」）
    #  每组都来自官方 templates/ 的真实参数（BPM / 调号 / 调式 / 乐器 /
    #  人声配置），映射到本节点的选项键。选定后覆盖对应参数并锁定，
    #  切回「自定义」即可自由调整。
    #  官方出处标注在每组注释里。
    # ═══════════════════════════════════════════════════════════
    _RECIPES = {
        "自定义 / Custom": {},

        # 官方 cinematic-pop-orchestral-ballad_0001：71 BPM / C# / major
        "🎬 电影感史诗抒情 / Cinematic Epic Ballad": {
            "音乐风格": "[官方] 管弦乐 / Orchestral",
            "风格融合": "不指定 / Unspecified",
            "速度": "慢速 60-75 / Slow 60-75 BPM",
            "调号": "降D / D-flat",
            "调式": "大调 / Major",
            "拍号": "4/4",
            "情绪氛围": "庄严 / Solemn",
            "情绪演变": "由静到扬 / Gradual Rise",
            "使用场景": "黄昏 / Sunset",
            "段落结构": "标准流行 / Standard Pop",
            "制作质感": "宽广开阔 / Wide Spacious",
            "主奏乐器": "钢琴 / Piano",
            "辅助乐器": "弦乐组 / Strings",
            "人声配置": "男声 / Male Vocal",
            "声部音区": "男中音 / Baritone",
            "人声音色": "温暖 / Warm",
            "人声唱法": "流行/通俗 / Pop Vocal",
            "和声伴唱": "多人叠唱 / Stacked Harmonies",
            "人声效果": "暖混响 / Warm Reverb",
            "合唱团": "大型混声合唱团 / Large Mixed SATB Choir",
        },

        # 官方 cinematic-orchestral-epic-choral_0004：67 BPM / Bb / major
        "🏛️ 史诗合唱圣咏 / Epic Choral": {
            "音乐风格": "[官方] 史诗 / Epic",
            "风格融合": "不指定 / Unspecified",
            "速度": "慢速 60-75 / Slow 60-75 BPM",
            "调号": "降B / B-flat",
            "调式": "大调 / Major",
            "拍号": "4/4",
            "情绪氛围": "庄严 / Solemn",
            "情绪演变": "由静到扬 / Gradual Rise",
            "使用场景": "黄昏 / Sunset",
            "段落结构": "标准流行 / Standard Pop",
            "制作质感": "大厅混响 / Hall Reverb",
            "主奏乐器": "弦乐组 / Strings",
            "辅助乐器": "法国号 / French Horn",
            "人声配置": "合唱 / Choir",
            "声部音区": "跟随风格 / Follow Style",
            "人声音色": "浑厚 / Deep Rich",
            "人声唱法": "美声 / Bel Canto",
            "和声伴唱": "跟随风格 / Follow Style",
            "人声效果": "暖混响 / Warm Reverb",
            "合唱团": "大型混声合唱团 / Large Mixed SATB Choir",
        },

        # 官方 mandopop-ballad_0001：70 BPM / F / major
        "🎤 华语流行金曲 / Mandopop Ballad": {
            "音乐风格": "[官方] 华语流行 / Mandopop",
            "风格融合": "不指定 / Unspecified",
            "速度": "慢速 60-75 / Slow 60-75 BPM",
            "调号": "F / F",
            "调式": "大调 / Major",
            "拍号": "4/4",
            "情绪氛围": "温暖 / Warm",
            "情绪演变": "起承转合 / Rise-Fall-Rise",
            "使用场景": "深夜耳机 / Late-night Headphones",
            "段落结构": "标准流行 / Standard Pop",
            "制作质感": "干净数字 / Clean Digital",
            "主奏乐器": "钢琴 / Piano",
            "辅助乐器": "弦乐组 / Strings",
            "人声配置": "女声 / Female Vocal",
            "声部音区": "女中音 / Mezzo-Soprano",
            "人声音色": "纯净 / Pure Clean",
            "人声唱法": "流行/通俗 / Pop Vocal",
            "和声伴唱": "双声部和声 / Double-Tracked Harmonies",
            "人声效果": "暖混响 / Warm Reverb",
            "合唱团": "无 / None",
        },

        # 官方 synth-pop-mandopop_0001：120 BPM / F# / major
        "🌃 复古合成器华语 / Retro Synth-Pop Mandopop": {
            "音乐风格": "[官方] 合成器浪潮 / Synthwave",
            "风格融合": "不指定 / Unspecified",
            "速度": "快速 110-135 / Fast 110-135 BPM",
            "调号": "升F / F-sharp",
            "调式": "大调 / Major",
            "拍号": "4/4",
            "情绪氛围": "怀旧 / Nostalgic",
            "情绪演变": "持续高能 / Steady Energetic",
            "使用场景": "驾驶 / Driving",
            "段落结构": "标准流行 / Standard Pop",
            "制作质感": "磁带 Lo-fi / Tape Lo-fi",
            "主奏乐器": "合成器 / Synthesizer",
            "辅助乐器": "鼓 / Drums",
            "人声配置": "女声 / Female Vocal",
            "声部音区": "女中音 / Mezzo-Soprano",
            "人声音色": "清亮 / Clear Bright",
            "人声唱法": "流行/通俗 / Pop Vocal",
            "和声伴唱": "双声部和声 / Double-Tracked Harmonies",
            "人声效果": "回声 / Echo",
            "合唱团": "无 / None",
        },

        # 官方 soul-gospel-infused-randb_0001：158 BPM / C / minor
        "🙏 灵魂福音 / Gospel Soul": {
            "音乐风格": "[官方] 福音 / Gospel",
            "风格融合": "不指定 / Unspecified",
            "速度": "极快 140+ / Very Fast 140+ BPM",
            "调号": "C / C",
            "调式": "小调 / Minor",
            "拍号": "4/4",
            "情绪氛围": "欢庆 / Celebratory",
            "情绪演变": "起承转合 / Rise-Fall-Rise",
            "使用场景": "派对 / Party",
            "段落结构": "标准流行 / Standard Pop",
            "制作质感": "大厅混响 / Hall Reverb",
            "主奏乐器": "电钢琴 / Electric Piano",
            "辅助乐器": "管风琴 / Organ",
            "人声配置": "女声 / Female Vocal",
            "声部音区": "女中音 / Mezzo-Soprano",
            "人声音色": "蜜糖 / Honeyed",
            "人声唱法": "颤音 / Vibrato",
            "和声伴唱": "多人叠唱 / Stacked Harmonies",
            "人声效果": "暖混响 / Warm Reverb",
            "合唱团": "福音合唱团 / Gospel Choir",
        },

        # 官方 a-cappella-choral-pop_0001：75 BPM / Eb / major
        "🎼 纯人声阿卡贝拉 / A Cappella": {
            "音乐风格": "[官方] 阿卡贝拉 / A Cappella",
            "风格融合": "不指定 / Unspecified",
            "速度": "慢速 60-75 / Slow 60-75 BPM",
            "调号": "降E / E-flat",
            "调式": "大调 / Major",
            "拍号": "4/4",
            "情绪氛围": "神圣 / Ethereal",
            "情绪演变": "持续平静 / Steady Calm",
            "使用场景": "冥想 / Meditation",
            "段落结构": "标准流行 / Standard Pop",
            "制作质感": "大厅混响 / Hall Reverb",
            "主奏乐器": "跟随风格 / Follow Style",
            "辅助乐器": "跟随风格 / Follow Style",
            "人声配置": "纯人声 / Acappella (Vocals Only)",
            "声部音区": "跟随风格 / Follow Style",
            "人声音色": "纯净 / Pure Clean",
            "人声唱法": "美声 / Bel Canto",
            "和声伴唱": "多人叠唱 / Stacked Harmonies",
            "人声效果": "暖混响 / Warm Reverb",
            "合唱团": "大型混声合唱团 / Large Mixed SATB Choir",
        },

        # 官方 traditional-chinese-folk-new-age-ballad_0001：69 BPM / C / major
        "🐉 国风民乐新纪元 / Chinese Folk New Age": {
            "音乐风格": "[官方] 国风民乐 / Chinese Folk",
            "风格融合": "不指定 / Unspecified",
            "速度": "慢速 60-75 / Slow 60-75 BPM",
            "调号": "C / C",
            "调式": "中国五声 / Chinese Pentatonic",
            "拍号": "4/4",
            "情绪氛围": "治愈 / Healing",
            "情绪演变": "持续平静 / Steady Calm",
            "使用场景": "晨间 / Morning",
            "段落结构": "标准流行 / Standard Pop",
            "制作质感": "宽广开阔 / Wide Spacious",
            "主奏乐器": "古筝 / Guzheng",
            "辅助乐器": "笛子 / Dizi",
            "人声配置": "女声 / Female Vocal",
            "声部音区": "女高音 / Soprano",
            "人声音色": "空灵 / Ethereal Airy",
            "人声唱法": "民族唱法 / Chinese Folk Singing",
            "和声伴唱": "伴唱垫底 / Backing Vocals",
            "人声效果": "暖混响 / Warm Reverb",
            "合唱团": "无 / None",
        },

        # 官方 pop-rock-power-ballad_0001：143 BPM / Ab / minor
        "⚡ 摇滚力量抒情 / Rock Power Ballad": {
            "音乐风格": "[官方] 摇滚 / Rock",
            "风格融合": "不指定 / Unspecified",
            "速度": "极快 140+ / Very Fast 140+ BPM",
            "调号": "降A / A-flat",
            "调式": "小调 / Minor",
            "拍号": "4/4",
            "情绪氛围": "高能 / Energetic",
            "情绪演变": "先抑后扬 / Suppressed→Erupt",
            "使用场景": "跑步 / Running",
            "段落结构": "含器乐间奏 / With Instrumental Break",
            "制作质感": "现场房间 / Live Room",
            "主奏乐器": "电吉他 / Electric Guitar",
            "辅助乐器": "鼓 / Drums",
            "人声配置": "男声 / Male Vocal",
            "声部音区": "男高音 / Tenor",
            "人声音色": "沧桑 / Weathered Gravelly",
            "人声唱法": "流行/通俗 / Pop Vocal",
            "和声伴唱": "多人叠唱 / Stacked Harmonies",
            "人声效果": "暖混响 / Warm Reverb",
            "合唱团": "无 / None",
        },

        # 官方 vocal-jazz-swing_0001：130 BPM / Bb / major
        "🎷 摇摆爵士大乐队 / Swing Big Band": {
            "音乐风格": "[官方] 摇摆爵士 / Swing & Big Band",
            "风格融合": "不指定 / Unspecified",
            "速度": "快速 110-135 / Fast 110-135 BPM",
            "调号": "降B / B-flat",
            "调式": "大调 / Major",
            "拍号": "4/4",
            "情绪氛围": "欢庆 / Celebratory",
            "情绪演变": "持续高能 / Steady Energetic",
            "使用场景": "派对 / Party",
            "段落结构": "含器乐间奏 / With Instrumental Break",
            "制作质感": "现场房间 / Live Room",
            "主奏乐器": "萨克斯 / Saxophone",
            "辅助乐器": "小号 / Trumpet",
            "人声配置": "女声 / Female Vocal",
            "声部音区": "女中音 / Mezzo-Soprano",
            "人声音色": "丝绒 / Velvety",
            "人声唱法": "颤音 / Vibrato",
            "和声伴唱": "伴唱垫底 / Backing Vocals",
            "人声效果": "干声无效果 / Dry (No FX)",
            "合唱团": "无 / None",
        },

        # 经典深夜 Lo-fi（对应官方 Lo-fi 参考范例写法）
        "🌙 深夜 Lo-fi / Late-night Lo-fi": {
            "音乐风格": "[官方] Lo-fi 嘻哈 / Lo-fi Hip-Hop",
            "风格融合": "不指定 / Unspecified",
            "速度": "慢速 60-75 / Slow 60-75 BPM",
            "调号": "降A / A-flat",
            "调式": "小调 / Minor",
            "拍号": "4/4",
            "情绪氛围": "放松 / Laid-back",
            "情绪演变": "持续平静 / Steady Calm",
            "使用场景": "雨夜 / Raining Outside",
            "段落结构": "简洁 / Compact",
            "制作质感": "磁带 Lo-fi / Tape Lo-fi",
            "主奏乐器": "电钢琴 / Electric Piano",
            "辅助乐器": "贝斯 / Bass",
            "人声配置": "柔和中性 / Soft Androgynous Vocal",
            "声部音区": "跟随风格 / Follow Style",
            "人声音色": "慵懒 / Lazy Laid-Back",
            "人声唱法": "半说半唱 / Half-Sung Half-Spoken",
            "和声伴唱": "伴唱垫底 / Backing Vocals",
            "人声效果": "磁带延迟 / Tape Delay",
            "合唱团": "无 / None",
        },

        # 官方 hip-hop-trap-with-traditional-chinese-fusion-elements_0001：95 BPM / G / minor
        "🇨🇳 国风嘻哈 / Guofeng Trap": {
            "音乐风格": "[官方] 嘻哈 / Hip-Hop",
            "风格融合": "不指定 / Unspecified",
            "速度": "中速 80-100 / Mid 80-100 BPM",
            "调号": "G / G",
            "调式": "小调 / Minor",
            "拍号": "4/4",
            "情绪氛围": "神秘 / Mysterious",
            "情绪演变": "先抑后扬 / Suppressed→Erupt",
            "使用场景": "通勤 / Commute",
            "段落结构": "标准流行 / Standard Pop",
            "制作质感": "宽广开阔 / Wide Spacious",
            "主奏乐器": "合成器 / Synthesizer",
            "辅助乐器": "古筝 / Guzheng",
            "人声配置": "男声 / Male Vocal",
            "声部音区": "男中音 / Baritone",
            "人声音色": "磁性 / Magnetic",
            "人声唱法": "说唱 / Rap Flow",
            "和声伴唱": "伴唱垫底 / Backing Vocals",
            "人声效果": "自动调音 / Auto-Tune",
            "合唱团": "无 / None",
        },
    }

    def _apply_recipe(self, p: dict) -> dict:
        """配方 != 自定义 时，用配方值覆盖对应参数（后端也覆盖，不依赖前端）。"""
        overrides = self._RECIPES.get(p.get("配方", "自定义 / Custom"))
        if not overrides:
            return p
        out = dict(p)
        for k, v in overrides.items():
            if k in out:
                out[k] = v
        return out

    # 兜底：历史工作流里可能残留旧版 UI 占位符写坏的非法下拉值（例如主奏乐器="—"），
    # 那会让 ComfyUI 默认组合校验直接拒掉整个 prompt
    # （"Value not in list: 主奏乐器: '—' not in (list of length 25)"）。
    # execution.py 里组合列表校验受 `x not in validate_function_inputs` 门控，
    # 所以在这里声明这几个输入即可让它们跳过默认校验；build 内部对这些参数
    # 一律走「查表兜底」，未知值等价于未指定。其余输入仍保留完整默认校验。
    @classmethod
    def VALIDATE_INPUTS(cls, 声部音区=None, 人声音色=None, 人声唱法=None, 和声伴唱=None,
                        人声效果=None, 合唱团=None, 主奏乐器=None, 辅助乐器=None):
        return True

    @classmethod
    def INPUT_TYPES(s):
        # 官方优先，补充靠后；组内保持定义顺序
        _keys = sorted(s._STYLES.keys(), key=lambda k: k in s._SUPPLEMENT_STYLES)
        style_list = [("[官方] " if k not in s._SUPPLEMENT_STYLES else "[补充] ") + k for k in _keys]
        fusion_list = ["不指定 / Unspecified"] + style_list
        return {
            "required": {

                "配方": (list(s._RECIPES.keys()), {
                    "default": "自定义 / Custom",
                    "tooltip": "一键完美配方：切换后会把下方参数自动切到该配方的预设值（官方 templates 的真实 BPM/调号/调式/乐器/人声搭配），参数仍可手动微调；切走再切回即可恢复预设值",
                }),
                "音乐风格": (style_list, {
                    "default": style_list[0],
                    "tooltip": "官方 Structured Caption 三段式：Global Metadata（genre/BPM/key/拍号/情绪/情绪演变/场景/制作）/ Vocal Details（配置/音区/音色/唱法/和声/效果）/ Arrangement（分段时间线）",
                }),
                "风格融合": (fusion_list, {
                    "default": "不指定 / Unspecified",
                    "tooltip": "官方 genre-router 支持双风格融合，副风格以 influences 形式并入 Global Metadata",
                }),
                "速度": (list(s._BPM_HINTS.keys()), {"default": "不指定 / Unspecified"}),
                "调式": (list(s._SCALE_HINTS.keys()), {"default": "不指定 / Unspecified"}),
                "调号": (list(s._KEY_HINTS.keys()), {"default": "不指定 / Unspecified"}),
                "拍号": (list(s._METER_HINTS.keys()), {"default": "不指定 / Unspecified"}),
                "情绪氛围": (list(s._MOOD_HINTS.keys()), {"default": "不指定 / Unspecified"}),
                "情绪演变": (list(s._CONTOUR_HINTS.keys()), {"default": "不指定 / Unspecified"}),
                "使用场景": (list(s._SCENE_HINTS.keys()), {"default": "不指定 / Unspecified"}),
                "段落结构": (list(s._STRUCTURE_HINTS.keys()), {"default": "跟随风格 / Follow Style"}),
                "主奏乐器": (["跟随风格 / Follow Style"] + list(s._INSTRUMENT_HINTS.keys()), {"default": "跟随风格 / Follow Style", "tooltip": "官方 Arrangement 支持指定 primary instrument（主奏乐器）"}),
                "辅助乐器": (["跟随风格 / Follow Style", "无 / None"] + list(s._INSTRUMENT_HINTS.keys()), {"default": "跟随风格 / Follow Style", "tooltip": "官方 Arrangement 支持指定 supporting instrument；选「无」配合主奏乐器=独奏"}),
                "制作质感": (list(s._TEXTURE_HINTS.keys()), {
                    "default": "跟随风格 / Follow Style",
                    "tooltip": "覆盖 caption 的制作质感描述。官方节点 cfg_scale（默认 1.5，CFG 引导强度）与 top_k（默认 50，采样候选截断）请在其高级参数中设置，本节点不改动",
                }),
                "人声配置": (list(s._VOCAL_CONFIG_HINTS.keys()), {"default": "跟随风格 / Follow Style"}),
                "合唱团": (list(s._CHOIR_HINTS.keys()), {
                    "default": "无 / None",
                    "tooltip": "官方合唱范式：合唱团声明写在 Vocal Gender & Timbre 子块（如 a large mixed SATB choir），SATB 编配细节写入 Harmony/Backing Vocals。人声配置=合唱 时会自动补大型混声合唱团",
                }),
                "声部音区": (list(s._REGISTER_HINTS.keys()), {"default": "跟随风格 / Follow Style"}),
                "人声音色": (list(s._VOCAL_TIMBRE_HINTS.keys()), {"default": "跟随风格 / Follow Style"}),
                "人声唱法": (list(s._VOCAL_STYLE_HINTS.keys()), {"default": "跟随风格 / Follow Style"}),
                "和声伴唱": (list(s._HARMONY_HINTS.keys()), {"default": "跟随风格 / Follow Style"}),
                "人声效果": (list(s._VOCAL_FX_HINTS.keys()), {"default": "跟随风格 / Follow Style"}),
                "自定义补充": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "tooltip": "自由文本，直接追加到 Global Metadata 末尾，用于枚举覆盖不到的长尾词（如 80年代卡带失真 / 日系动漫燃系女高音）",
                }),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("caption",)
    FUNCTION = "build"
    CATEGORY = "JZL/MiniMax"

    @staticmethod
    def _en(label: str) -> str:
        return label.split(" / ")[-1]

    @staticmethod
    def _cap(text: str) -> str:
        """去首尾空白与尾部句号，并把首字母大写（用于把维度提示拼成独立子句）。"""
        t = (text or "").strip().rstrip(".")
        return (t[:1].upper() + t[1:]) if t else t

    @staticmethod
    def _dot(text: str) -> str:
        """去首尾空白，并保证句尾有句号。"""
        t = (text or "").strip().rstrip(".")
        return (t + ".") if t else ""

    @staticmethod
    def _low(text: str) -> str:
        """首字母小写（用于把风格库的整句嵌进从句）。"""
        t = (text or "").strip()
        return (t[:1].lower() + t[1:]) if t else t

    @staticmethod
    def _art(text: str) -> str:
        """按首字母返回 a / an，避免拼接时的冠词错误。"""
        return "an" if (text or "").strip()[:1].lower() in "aeiou" else "a"

    @staticmethod
    def _sentences(text: str) -> list:
        """按句号切分英文散文（保留句尾句号），用于拆成官方的 Metadata 子块。"""
        return [p.strip() for p in re.split(r"(?<=\.)\s+", text.strip()) if p.strip()]

    def _compose_vocal(self, style: dict, config_key: str, register_key: str, timbre_key: str,
                       style_key: str, harmony_key: str, fx_key: str,
                       choir_key: str = "无 / None") -> str:
        v = style["vocal"]

        if config_key == "无人声 / Instrumental (No Vocals)":
            return "\n".join([
                "Vocal Gender & Timbre: Instrumental — no vocals at all; every melody is "
                "carried by instruments.",
                f"Vocal Style: {self._dot(v['style'])}",
                "Harmony/Backing Vocals: None — the arrangement is entirely instrumental.",
                f"Vocal FX: {self._dot(v['fx'])}",
            ])

        # 官方合唱范式：人声配置=合唱 时若未选合唱团，自动补「大型混声 SATB」
        choir_k = choir_key if choir_key in self._CHOIR_HINTS else "无 / None"
        if choir_k == "无 / None" and config_key == "合唱 / Choir":
            choir_k = "大型混声合唱团 / Large Mixed SATB Choir"
        choir = self._CHOIR_HINTS[choir_k]

        config = self._VOCAL_CONFIG_HINTS.get(config_key, "")
        register = self._REGISTER_HINTS.get(register_key, "")
        timbre = self._VOCAL_TIMBRE_HINTS.get(timbre_key, "")
        delivery = self._VOCAL_STYLE_HINTS.get(style_key, "")
        harmony = self._HARMONY_HINTS.get(harmony_key, "")
        fx = self._VOCAL_FX_HINTS.get(fx_key, "")

        blocks = []

        # ── Vocal Gender & Timbre（官方：合唱团在此子块声明）──
        if config_key == "合唱 / Choir":
            bits = " ".join(p for p in (timbre, register) if p)
            core = f"A powerful {choir['gt']}" if choir["gt"] else "A full choir"
            if bits:
                core += f", with {bits} voices carrying the top line"
            gt_parts = [f"{core} serves as the primary vocal force"]
            if choir["choir_line"]:
                gt_parts.append(choir["choir_line"])
            blocks.append(f"Vocal Gender & Timbre: {self._dot('. '.join(gt_parts))}")
        elif config_key == "纯人声 / Acappella (Vocals Only)":
            parts = [p for p in (timbre, register) if p]
            subject = self._cap(" ".join(parts)) if parts else "Lead vocal"
            if choir["gt"]:
                subject += f", together with {self._art(choir['gt'])} {choir['gt']}"
            gt_parts = [f"{subject}, performed a cappella with no instrumental accompaniment"]
            if choir["choir_line"]:
                gt_parts.append(choir["choir_line"])
            blocks.append(f"Vocal Gender & Timbre: {self._dot('. '.join(gt_parts))}")
        else:
            gt = " ".join(p for p in (timbre, register, config) if p)
            gt_parts = [self._cap(gt) if gt else self._cap(v["timbre"])]
            if choir["gt"]:
                gt_parts.append(f"Backed by {self._art(choir['gt'])} {choir['gt']}")
                if choir["choir_line"]:
                    gt_parts.append(choir["choir_line"])
            blocks.append(f"Vocal Gender & Timbre: {self._dot('. '.join(gt_parts))}")

        blocks.append(
            f"Vocal Style: {self._cap(delivery)}." if delivery else f"Vocal Style: {self._dot(v['style'])}"
        )

        # ── Harmony/Backing Vocals（官方：SATB 编配细节在此子块）──
        harm_parts = []
        if choir["harm"]:
            harm_parts.append(choir["harm"])
        if harmony and not (choir["harm"] and harmony.strip().lower() == "no harmony"):
            harm_parts.append(self._cap(harmony))
        blocks.append(
            f"Harmony/Backing Vocals: {self._dot('. '.join(harm_parts))}"
            if harm_parts
            else f"Harmony/Backing Vocals: {self._dot(v['harmony'])}"
        )
        blocks.append(f"Vocal FX: {self._cap(fx)}." if fx else f"Vocal FX: {self._dot(v['fx'])}")
        return "\n".join(blocks)

    def _resolve_style(self, 音乐风格: str) -> dict:
        style_key = 音乐风格
        for prefix in ("[官方] ", "[补充] "):
            if style_key.startswith(prefix):
                style_key = style_key[len(prefix):]
                break
        style = self._STYLES.get(style_key)
        if style is None:
            raise ValueError(f'未知音乐风格: "{音乐风格}"')
        return style

    def _compose_global(self, style: dict, 风格融合: str, 速度: str, 调式: str, 调号: str,
                        拍号: str, 情绪氛围: str, 情绪演变: str, 使用场景: str, 制作质感: str,
                        自定义补充: str = "") -> str:
        sents = self._sentences(style["global"])
        genre = sents[0] if sents else ""
        progression = sents[1] if len(sents) > 1 else ""
        scene = sents[2] if len(sents) > 2 else ""
        sonics = " ".join(sents[3:]) if len(sents) > 3 else ""

        # Basic Attributes：官方句式 “bpm is X. key is Y, and scale is Z. <genre>.”
        attrs = []
        bpm = self._BPM_HINTS.get(速度, "")
        if bpm:
            attrs.append(f"bpm is {bpm.replace(' BPM', '')}")
        key = self._KEY_HINTS.get(调号, "")
        scale = self._SCALE_HINTS.get(调式, "")
        if key and scale:
            attrs.append(f"key is {key}, and scale is {scale}")
        elif key:
            attrs.append(f"key is {key}")
        elif scale:
            attrs.append(f"scale is {scale}")
        meter = self._METER_HINTS.get(拍号, "")
        if meter:
            attrs.append(meter)
        if genre:
            attrs.append(self._cap(genre))
        basic = ". ".join(attrs).rstrip(".") + "." if attrs else ""

        prog_parts = []
        if progression:
            prog_parts.append(self._cap(progression))
        mood = self._MOOD_HINTS.get(情绪氛围, "")
        if mood:
            prog_parts.append(self._cap(mood))
        contour = self._CONTOUR_HINTS.get(情绪演变, "")
        if contour:
            prog_parts.append(self._cap(contour))
        prog = ". ".join(prog_parts) + "." if prog_parts else ""

        scene_parts = []
        if scene:
            scene_parts.append(self._cap(scene))
        sc = self._SCENE_HINTS.get(使用场景, "")
        if sc:
            scene_parts.append(self._cap(sc))
        scene_text = ". ".join(scene_parts) + "." if scene_parts else ""

        sonics_parts = []
        if sonics:
            sonics_parts.append(self._cap(sonics))
        texture = self._TEXTURE_HINTS.get(制作质感, "")
        if texture:
            sonics_parts.append(self._cap(texture))
        if "不指定" not in 风格融合:
            sonics_parts.append(f"Fused with {self._en(风格融合)} influences")
        if 自定义补充 and 自定义补充.strip():
            sonics_parts.append(self._cap(自定义补充))
        sonics_text = ". ".join(sonics_parts) + "." if sonics_parts else ""

        blocks = []
        if basic:
            blocks.append(f"Basic Attributes: {basic}")
        if prog:
            blocks.append(f"Global Emotional Progression: {prog}")
        if scene_text:
            blocks.append(f"Application Scenarios & Imagery: {scene_text}")
        if sonics_text:
            blocks.append(f"Sonics & Production Profile: {sonics_text}")
        return "\n".join(blocks)

    def _compose_arrangement(self, style: dict, 段落结构: str, 主奏乐器: str, 辅助乐器: str,
                             vocal_only: bool = False, extra_timeline: str = "") -> str:
        a = style["arrangement"]
        lead = self._INSTRUMENT_HINTS.get(主奏乐器, "")
        support = "none" if 辅助乐器 == "无 / None" else self._INSTRUMENT_HINTS.get(辅助乐器, "")

        if vocal_only:
            primary = (
                "The human voice serves as the sole instrument, fulfilling all melodic, harmonic, "
                "and rhythmic roles"
            )
            secondary = "Layered vocal harmonies carry the harmony, with beatbox percussion replacing the drum kit"
            groove = "Percussive consonant articulation and beatbox patterns provide the entire pulse"
            embellishments = "Wordless vocal pads and dynamic layering replace instrumental builds"
            timeline = "There is no traditional instrumental accompaniment at any point"
        else:
            primary, secondary = a["primary"], a["secondary"]
            groove, embellishments, timeline = a["groove"], a["embellishments"], a["timeline"]
            if lead and support == "none":
                primary = (
                    f"{self._cap(lead)} as the sole melodic instrument, with no other melodic instruments "
                    f"— a solo {lead} piece carries every melody with expressive phrasing"
                )
                secondary = "None — a solo setting where one instrument covers all melodic roles"
                timeline = (
                    "Opening: a slow lyrical phrase. Middle: the melody rises and falls with ornamentation. "
                    "Closing: a final sustained note decays into silence"
                )
            elif lead and support:
                primary = (
                    f"{self._cap(lead)} carrying the lead melodic role, shaping the main melodic "
                    f"and harmonic content throughout"
                )
                secondary = (
                    f"{self._cap(support)} layered beneath as the secondary voice, filling the "
                    f"harmonic and rhythmic space"
                )
            elif lead:
                primary = (
                    f"{self._cap(lead)} carrying the lead melodic role throughout, with the "
                    f"remaining instruments receding into support"
                )
            elif support and support != "none":
                secondary = (
                    f"{self._cap(support)} layered beneath as the secondary voice, filling the "
                    f"harmonic and rhythmic space"
                )

        # 双人对唱：把官方风格的人声进退场句并入 Section Timeline（双重锁定）
        if extra_timeline:
            timeline = f"{timeline.rstrip('.')}. {extra_timeline}"

        blocks = [
            "Instrument Lifecycle Description (Primary/Secondary Layering):",
            f"Primary: {self._dot(primary)}",
            f"Secondary: {self._dot(secondary)}",
            f"Groove & Foundation Progression: {self._dot(groove)}",
            f"Embellishments, Textures & Spatial FX: {self._dot(embellishments)}",
            f"Section Timeline: {self._dot(timeline)}",
        ]
        structure = self._STRUCTURE_HINTS.get(段落结构, "")
        if structure:
            blocks.append(f"Section Structure: {self._dot(structure)}")
        return "\n".join(blocks)

    def build(self, 配方: str, 音乐风格: str, 风格融合: str, 速度: str, 调式: str, 调号: str,
              拍号: str, 情绪氛围: str, 情绪演变: str, 使用场景: str, 段落结构: str, 主奏乐器: str,
              辅助乐器: str, 制作质感: str, 人声配置: str, 合唱团: str,
              声部音区: str, 人声音色: str, 人声唱法: str, 和声伴唱: str, 人声效果: str,
              自定义补充: str) -> tuple[str]:
        p = self._apply_recipe({k: v for k, v in locals().items() if k != "self"})
        style = self._resolve_style(p["音乐风格"])

        global_text = self._compose_global(
            style, p["风格融合"], p["速度"], p["调式"], p["调号"], p["拍号"],
            p["情绪氛围"], p["情绪演变"], p["使用场景"], p["制作质感"], p["自定义补充"],
        )
        vocal_text = self._compose_vocal(
            style, p["人声配置"], p["声部音区"], p["人声音色"], p["人声唱法"],
            p["和声伴唱"], p["人声效果"], p["合唱团"],
        )
        vocal_only = p["人声配置"] == "纯人声 / Acappella (Vocals Only)"
        arrangement_text = self._compose_arrangement(
            style, p["段落结构"], p["主奏乐器"], p["辅助乐器"], vocal_only=vocal_only
        )

        caption = (
            f"Global Metadata\n{global_text}\n\n"
            f"Vocal Details\n{vocal_text}\n\n"
            f"Arrangement\n{arrangement_text}"
        )
        return (caption,)


class JZL_MiniMaxMusicCaptionDuet(JZL_MiniMaxMusicCaption):
    """MiniMax Music3 双人版提示词预设 — 两个角色各自完整的人声参数 + 角色分工"""

    _ROLE_ASSIGN_HINTS = {
        "不分主次 / Equal Lead": "Singer A and Singer B share the lead equally",
        "A主B和 / A Lead B Harmony": "Singer A sings the lead melody while Singer B provides harmonies",
        "B主A和 / B Lead A Harmony": "Singer B sings the lead melody while Singer A provides harmonies",
        "A主歌B副歌 / A Verses B Chorus": "Singer A sings the verses while Singer B takes the chorus",
        "B主歌A副歌 / B Verses A Chorus": "Singer B sings the verses while Singer A takes the chorus",
        "轮流对唱 / Call-and-Response": "Singer A and Singer B alternate in call-and-response",
    }

    # 官方主副声部标记：Singer A (Male Lead) / Singer B (Female Lead)
    _ROLE_LEAD_FLAGS = {
        "不分主次 / Equal Lead": (False, False),
        "A主B和 / A Lead B Harmony": (True, False),
        "B主A和 / B Lead A Harmony": (False, True),
        "A主歌B副歌 / A Verses B Chorus": (True, True),
        "B主歌A副歌 / B Verses A Chorus": (True, True),
        "轮流对唱 / Call-and-Response": (False, False),
    }

    # 官方写法把性别放在括号里：Singer A (Male)
    _ROLE_GENDER_LABEL = {
        "女声 / Female Vocal": "Female",
        "男声 / Male Vocal": "Male",
        "童声 / Child Vocal": "Child",
        "柔和中性 / Soft Androgynous Vocal": "Androgynous",
    }

    # Arrangement 时间轴里的人声进退场（官方风格措辞，与 Vocal Details 双重锁定）
    _ROLE_HANDOVER_HINTS = {
        "不分主次 / Equal Lead": "Singer A and Singer B trade the lead evenly across sections, alternating phrases and converging in unison on the hooks",
        "A主B和 / A Lead B Harmony": "Singer A carries the lead across all sections while Singer B reinforces with harmony lines on the choruses",
        "B主A和 / B Lead A Harmony": "Singer B carries the lead across all sections while Singer A reinforces with harmony lines on the choruses",
        "A主歌B副歌 / A Verses B Chorus": "Verses are carried by Singer A over the core instrumentation, choruses are taken by Singer B, and both voices stack together in the final chorus",
        "B主歌A副歌 / B Verses A Chorus": "Verses are carried by Singer B over the core instrumentation, choruses are taken by Singer A, and both voices stack together in the final chorus",
        "轮流对唱 / Call-and-Response": "Verses alternate line by line in call-and-response between Singer A and Singer B, with both voices converging in tight harmony on the choruses",
    }

    _ROLE_CONFIG_HINTS = {
        "女声 / Female Vocal": "female vocal",
        "男声 / Male Vocal": "male vocal",
        "童声 / Child Vocal": "child's voice",
        "柔和中性 / Soft Androgynous Vocal": "soft androgynous vocal",
    }

    @classmethod
    def INPUT_TYPES(cls):
        _keys = sorted(cls._STYLES.keys(), key=lambda k: k in cls._SUPPLEMENT_STYLES)
        style_list = [("[官方] " if k not in cls._SUPPLEMENT_STYLES else "[补充] ") + k for k in _keys]
        fusion_list = ["不指定 / Unspecified"] + style_list
        return {
            "required": {
                "配方": (list(cls._RECIPES.keys()), {
                    "default": "自定义 / Custom",
                    "tooltip": "一键完美配方（含双人角色 A/B 声部搭配）：切换后会把下方参数自动切到该配方的预设值，仍可手动微调；切走再切回即可恢复预设值",
                }),
                "音乐风格": (style_list, {"default": style_list[0]}),
                "风格融合": (fusion_list, {"default": "不指定 / Unspecified"}),
                "速度": (list(cls._BPM_HINTS.keys()), {"default": "不指定 / Unspecified"}),
                "调式": (list(cls._SCALE_HINTS.keys()), {"default": "不指定 / Unspecified"}),
                "调号": (list(cls._KEY_HINTS.keys()), {"default": "不指定 / Unspecified"}),
                "拍号": (list(cls._METER_HINTS.keys()), {"default": "不指定 / Unspecified"}),
                "情绪氛围": (list(cls._MOOD_HINTS.keys()), {"default": "不指定 / Unspecified"}),
                "情绪演变": (list(cls._CONTOUR_HINTS.keys()), {"default": "不指定 / Unspecified"}),
                "使用场景": (list(cls._SCENE_HINTS.keys()), {"default": "不指定 / Unspecified"}),
                "段落结构": (list(cls._STRUCTURE_HINTS.keys()), {"default": "跟随风格 / Follow Style"}),
                "主奏乐器": (["跟随风格 / Follow Style"] + list(cls._INSTRUMENT_HINTS.keys()), {"default": "跟随风格 / Follow Style"}),
                "辅助乐器": (["跟随风格 / Follow Style", "无 / None"] + list(cls._INSTRUMENT_HINTS.keys()), {"default": "跟随风格 / Follow Style"}),
                "制作质感": (list(cls._TEXTURE_HINTS.keys()), {"default": "跟随风格 / Follow Style"}),
                "纯人声无伴奏": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "开启后整首为纯人声无伴奏（acappella），忽略主奏/辅助乐器",
                }),
                "合唱团": (list(cls._CHOIR_HINTS.keys()), {
                    "default": "无 / None",
                    "tooltip": "官方合唱范式：大型混声合唱团会写成「The track features a mixed ensemble comprising Singer A (...), Singer B (...), and a large SATB choir」，SATB 编配细节写入 Harmony/Backing Vocals",
                }),
                "角色分工": (list(cls._ROLE_ASSIGN_HINTS.keys()), {"default": "不分主次 / Equal Lead"}),
                "角色A配置": (list(cls._ROLE_CONFIG_HINTS.keys()), {"default": "女声 / Female Vocal"}),
                "角色A音区": (list(cls._REGISTER_HINTS.keys()), {"default": "跟随风格 / Follow Style"}),
                "角色A音色": (list(cls._VOCAL_TIMBRE_HINTS.keys()), {"default": "跟随风格 / Follow Style"}),
                "角色A唱法": (list(cls._VOCAL_STYLE_HINTS.keys()), {"default": "跟随风格 / Follow Style"}),
                "角色B配置": (list(cls._ROLE_CONFIG_HINTS.keys()), {"default": "男声 / Male Vocal"}),
                "角色B音区": (list(cls._REGISTER_HINTS.keys()), {"default": "跟随风格 / Follow Style"}),
                "角色B音色": (list(cls._VOCAL_TIMBRE_HINTS.keys()), {"default": "跟随风格 / Follow Style"}),
                "角色B唱法": (list(cls._VOCAL_STYLE_HINTS.keys()), {"default": "跟随风格 / Follow Style"}),
                "和声伴唱": (list(cls._HARMONY_HINTS.keys()), {"default": "跟随风格 / Follow Style"}),
                "人声效果": (list(cls._VOCAL_FX_HINTS.keys()), {"default": "跟随风格 / Follow Style"}),
                "自定义补充": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "tooltip": "自由文本，直接追加到 Global Metadata 末尾，用于枚举覆盖不到的长尾词（如 80年代卡带失真 / 日系动漫燃系女高音）",
                }),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("caption",)
    FUNCTION = "build"
    CATEGORY = "JZL/MiniMax"

    def _singer_label(self, tag: str, config_key: str, is_lead: bool) -> str:
        """官方写法：Singer A (Male) / Singer A (Male Lead)"""
        gender = self._ROLE_GENDER_LABEL.get(config_key, "")
        inner = f"{gender}{' Lead' if is_lead else ''}".strip()
        return f"Singer {tag} ({inner})" if inner else f"Singer {tag}"

    def _compose_role_vocal(self, register_key: str, timbre_key: str, style_timbre: str) -> str:
        """返回角色的音色名词短语（官方句式：Singer A possesses a warm, resonant baritone）。"""
        register = self._REGISTER_HINTS.get(register_key, "")
        timbre = self._VOCAL_TIMBRE_HINTS.get(timbre_key, "")
        bits = " ".join(p for p in (timbre, register) if p)
        if bits:
            return f"{bits} timbre"
        low = self._low(style_timbre)
        if low and "instrumental" not in low.lower() and "no vocal" not in low.lower():
            return low
        return ""

    def build(self, 配方: str, 音乐风格: str, 风格融合: str, 速度: str, 调式: str, 调号: str,
              拍号: str, 情绪氛围: str, 情绪演变: str, 使用场景: str, 段落结构: str, 主奏乐器: str,
              辅助乐器: str, 制作质感: str, 纯人声无伴奏: bool, 合唱团: str,
              角色分工: str, 角色A配置: str, 角色A音区: str, 角色A音色: str, 角色A唱法: str,
              角色B配置: str, 角色B音区: str, 角色B音色: str, 角色B唱法: str,
              和声伴唱: str, 人声效果: str, 自定义补充: str) -> tuple[str]:
        p = self._apply_recipe({k: v for k, v in locals().items() if k != "self"})
        style = self._resolve_style(p["音乐风格"])
        global_text = self._compose_global(
            style, p["风格融合"], p["速度"], p["调式"], p["调号"], p["拍号"],
            p["情绪氛围"], p["情绪演变"], p["使用场景"], p["制作质感"], p["自定义补充"],
        )

        v = style["vocal"]
        choir = self._CHOIR_HINTS.get(p["合唱团"], self._CHOIR_HINTS["无 / None"])
        lead_a, lead_b = self._ROLE_LEAD_FLAGS.get(p["角色分工"], (False, False))
        label_a = self._singer_label("A", p["角色A配置"], lead_a)
        label_b = self._singer_label("B", p["角色B配置"], lead_b)
        a = self._compose_role_vocal(p["角色A音区"], p["角色A音色"], v["timbre"])
        b = self._compose_role_vocal(p["角色B音区"], p["角色B音色"], v["timbre"])
        assign = self._ROLE_ASSIGN_HINTS.get(p["角色分工"], "")
        harmony = self._HARMONY_HINTS.get(p["和声伴唱"], "")
        fx = self._VOCAL_FX_HINTS.get(p["人声效果"], "")
        纯人声无伴奏 = bool(p["纯人声无伴奏"])

        blocks = []

        # ── Vocal Gender & Timbre：官方对唱/合唱写法 ──
        #    官方原句：Singer A (Male) and Singer B (Female). Singer A possesses a warm ... baritone.
        #    官方含合唱：The track features a mixed ensemble comprising Singer A (Male Lead),
        #               Singer B (Female Lead), and a large Satb Choir.
        if 纯人声无伴奏:
            head = "An a cappella duet with no instrumental accompaniment"
            if choir["gt"]:
                head += f", joined by {self._art(choir['gt'])} {choir['gt']}"
            gt_parts = [head]
        elif choir["gt"]:
            gt_parts = [
                f"The track features a mixed ensemble comprising {label_a}, {label_b}, "
                f"and {self._art(choir['gt'])} {choir['gt']}"
            ]
        else:
            gt_parts = [f"{label_a} and {label_b}"]
        # 官方句式：第二句起只用 Singer A / Singer B，不重复括号里的声部标记
        fallback = self._low(v["timbre"])
        if a and b and a == b:
            # 两人音色一致（多为都选了「跟随风格」）：合并为一句，避免重复
            if a == fallback:
                gt_parts.append(f"Both singers keep the style's signature timbre: {a}")
            else:
                gt_parts.append(f"Both singers share the same timbre: {a}")
        else:
            if a:
                gt_parts.append(f"Singer A possesses {self._art(a)} {a}")
            if b:
                gt_parts.append(f"Singer B features {self._art(b)} {b}")
        if choir["choir_line"]:
            gt_parts.append(choir["choir_line"])
        blocks.append(f"Vocal Gender & Timbre: {self._dot('. '.join(gt_parts))}")

        # Vocal Style：角色分工 + 各自唱法（未指定时用风格自带描述兜底）
        style_bits = []
        if assign:
            style_bits.append(assign)
        ad = self._VOCAL_STYLE_HINTS.get(角色A唱法, "")
        bd = self._VOCAL_STYLE_HINTS.get(角色B唱法, "")
        if ad and bd:
            style_bits.append(f"Singer A sings with {ad}, while Singer B sings with {bd}")
        elif ad or bd:
            style_bits.append(f"{'Singer A' if ad else 'Singer B'} sings with {ad or bd}")
        if not style_bits:
            style_bits.append(v["style"])
        blocks.append(f"Vocal Style: {self._dot('. '.join(style_bits))}")

        # ── Harmony/Backing Vocals（官方：SATB 编配细节在此子块）──
        harm_parts = []
        if choir["harm"]:
            harm_parts.append(choir["harm"])
        if harmony and not (choir["harm"] and harmony.strip().lower() == "no harmony"):
            harm_parts.append(self._cap(harmony))
        blocks.append(
            f"Harmony/Backing Vocals: {self._dot('. '.join(harm_parts))}"
            if harm_parts
            else f"Harmony/Backing Vocals: {self._dot(v['harmony'])}"
        )
        blocks.append(f"Vocal FX: {self._cap(fx)}." if fx else f"Vocal FX: {self._dot(v['fx'])}")
        vocal_text = "\n".join(blocks)

        # Section Timeline 并入人声进退场，与 Vocal Details 双重锁定
        arrangement_text = self._compose_arrangement(
            style, p["段落结构"], p["主奏乐器"], p["辅助乐器"],
            vocal_only=纯人声无伴奏,
            extra_timeline=self._ROLE_HANDOVER_HINTS.get(p["角色分工"], ""),
        )

        caption = (
            f"Global Metadata\n{global_text}\n\n"
            f"Vocal Details\n{vocal_text}\n\n"
            f"Arrangement\n{arrangement_text}"
        )
        return (caption,)


# ═══════════════════════════════════════════════════════════
#  双人版配方：在基础配方上叠加「角色 A / B」声部搭配
#  A/B 的性别与音区刻意做成互补（女高音 × 男中音 等），
#  让新手一键就能得到稳定的男女对唱 / 合唱分工。
# ═══════════════════════════════════════════════════════════
_SINGLE_ONLY_VOCAL_KEYS = ("人声配置", "声部音区", "人声音色", "人声唱法")

_DUET_CAST = {
    "🎬 电影感史诗抒情 / Cinematic Epic Ballad": {
        "纯人声无伴奏": False,
        "角色分工": "A主歌B副歌 / A Verses B Chorus",
        "角色A配置": "女声 / Female Vocal", "角色A音区": "女高音 / Soprano",
        "角色A音色": "空灵 / Ethereal Airy", "角色A唱法": "流行/通俗 / Pop Vocal",
        "角色B配置": "男声 / Male Vocal", "角色B音区": "男中音 / Baritone",
        "角色B音色": "温暖 / Warm", "角色B唱法": "流行/通俗 / Pop Vocal",
    },
    "🏛️ 史诗合唱圣咏 / Epic Choral": {
        "纯人声无伴奏": False,
        "角色分工": "A主歌B副歌 / A Verses B Chorus",
        "角色A配置": "男声 / Male Vocal", "角色A音区": "男高音 / Tenor",
        "角色A音色": "浑厚 / Deep Rich", "角色A唱法": "美声 / Bel Canto",
        "角色B配置": "女声 / Female Vocal", "角色B音区": "女高音 / Soprano",
        "角色B音色": "空灵 / Ethereal Airy", "角色B唱法": "美声 / Bel Canto",
    },
    "🎤 华语流行金曲 / Mandopop Ballad": {
        "纯人声无伴奏": False,
        "角色分工": "A主歌B副歌 / A Verses B Chorus",
        "角色A配置": "女声 / Female Vocal", "角色A音区": "女中音 / Mezzo-Soprano",
        "角色A音色": "纯净 / Pure Clean", "角色A唱法": "流行/通俗 / Pop Vocal",
        "角色B配置": "男声 / Male Vocal", "角色B音区": "男中音 / Baritone",
        "角色B音色": "磁性 / Magnetic", "角色B唱法": "流行/通俗 / Pop Vocal",
    },
    "🌃 复古合成器华语 / Retro Synth-Pop Mandopop": {
        "纯人声无伴奏": False,
        "角色分工": "不分主次 / Equal Lead",
        "角色A配置": "女声 / Female Vocal", "角色A音区": "女中音 / Mezzo-Soprano",
        "角色A音色": "清亮 / Clear Bright", "角色A唱法": "流行/通俗 / Pop Vocal",
        "角色B配置": "男声 / Male Vocal", "角色B音区": "男高音 / Tenor",
        "角色B音色": "清亮 / Clear Bright", "角色B唱法": "流行/通俗 / Pop Vocal",
    },
    "🙏 灵魂福音 / Gospel Soul": {
        "纯人声无伴奏": False,
        "角色分工": "不分主次 / Equal Lead",
        "角色A配置": "女声 / Female Vocal", "角色A音区": "女中音 / Mezzo-Soprano",
        "角色A音色": "蜜糖 / Honeyed", "角色A唱法": "颤音 / Vibrato",
        "角色B配置": "男声 / Male Vocal", "角色B音区": "男中音 / Baritone",
        "角色B音色": "磁性 / Magnetic", "角色B唱法": "颤音 / Vibrato",
    },
    "🎼 纯人声阿卡贝拉 / A Cappella": {
        "纯人声无伴奏": True,
        "角色分工": "不分主次 / Equal Lead",
        "角色A配置": "女声 / Female Vocal", "角色A音区": "女高音 / Soprano",
        "角色A音色": "纯净 / Pure Clean", "角色A唱法": "美声 / Bel Canto",
        "角色B配置": "男声 / Male Vocal", "角色B音区": "男中音 / Baritone",
        "角色B音色": "浑厚 / Deep Rich", "角色B唱法": "美声 / Bel Canto",
    },
    "🐉 国风民乐新纪元 / Chinese Folk New Age": {
        "纯人声无伴奏": False,
        "角色分工": "A主歌B副歌 / A Verses B Chorus",
        "角色A配置": "女声 / Female Vocal", "角色A音区": "女高音 / Soprano",
        "角色A音色": "空灵 / Ethereal Airy", "角色A唱法": "民族唱法 / Chinese Folk Singing",
        "角色B配置": "男声 / Male Vocal", "角色B音区": "男中音 / Baritone",
        "角色B音色": "浑厚 / Deep Rich", "角色B唱法": "民族唱法 / Chinese Folk Singing",
    },
    "⚡ 摇滚力量抒情 / Rock Power Ballad": {
        "纯人声无伴奏": False,
        "角色分工": "轮流对唱 / Call-and-Response",
        "角色A配置": "男声 / Male Vocal", "角色A音区": "男高音 / Tenor",
        "角色A音色": "沧桑 / Weathered Gravelly", "角色A唱法": "流行/通俗 / Pop Vocal",
        "角色B配置": "女声 / Female Vocal", "角色B音区": "女中音 / Mezzo-Soprano",
        "角色B音色": "烟嗓 / Smoky Husky", "角色B唱法": "流行/通俗 / Pop Vocal",
    },
    "🎷 摇摆爵士大乐队 / Swing Big Band": {
        "纯人声无伴奏": False,
        "角色分工": "轮流对唱 / Call-and-Response",
        "角色A配置": "女声 / Female Vocal", "角色A音区": "女中音 / Mezzo-Soprano",
        "角色A音色": "丝绒 / Velvety", "角色A唱法": "颤音 / Vibrato",
        "角色B配置": "男声 / Male Vocal", "角色B音区": "男中音 / Baritone",
        "角色B音色": "温暖 / Warm", "角色B唱法": "颤音 / Vibrato",
    },
    "🌙 深夜 Lo-fi / Late-night Lo-fi": {
        "纯人声无伴奏": False,
        "角色分工": "不分主次 / Equal Lead",
        "角色A配置": "柔和中性 / Soft Androgynous Vocal", "角色A音区": "跟随风格 / Follow Style",
        "角色A音色": "慵懒 / Lazy Laid-Back", "角色A唱法": "半说半唱 / Half-Sung Half-Spoken",
        "角色B配置": "男声 / Male Vocal", "角色B音区": "男中音 / Baritone",
        "角色B音色": "气声 / Breathy", "角色B唱法": "半说半唱 / Half-Sung Half-Spoken",
    },
    "🇨🇳 国风嘻哈 / Guofeng Trap": {
        "纯人声无伴奏": False,
        "角色分工": "A主歌B副歌 / A Verses B Chorus",
        "角色A配置": "男声 / Male Vocal", "角色A音区": "男中音 / Baritone",
        "角色A音色": "磁性 / Magnetic", "角色A唱法": "说唱 / Rap Flow",
        "角色B配置": "女声 / Female Vocal", "角色B音区": "女中音 / Mezzo-Soprano",
        "角色B音色": "空灵 / Ethereal Airy", "角色B唱法": "吟唱 / Chant",
    },
}

# 双人专属配方（对唱情歌，官方 cinematic-pop-orchestral-ballad 的对唱演绎）
_DUET_ONLY_RECIPES = {
    "💞 男女对唱情歌 / Duet Love Ballad": {
        "音乐风格": "[官方] 流行 / Pop",
        "风格融合": "不指定 / Unspecified",
        "速度": "慢速 60-75 / Slow 60-75 BPM",
        "调号": "降E / E-flat",
        "调式": "大调 / Major",
        "拍号": "4/4",
        "情绪氛围": "浪漫 / Romantic",
        "情绪演变": "由静到扬 / Gradual Rise",
        "使用场景": "深夜耳机 / Late-night Headphones",
        "段落结构": "标准流行 / Standard Pop",
        "制作质感": "干净数字 / Clean Digital",
        "主奏乐器": "电钢琴 / Electric Piano",
        "辅助乐器": "弦乐组 / Strings",
        "纯人声无伴奏": False,
        "合唱团": "小型和声组 / Small Backing Group",
        "角色分工": "轮流对唱 / Call-and-Response",
        "角色A配置": "男声 / Male Vocal", "角色A音区": "男中音 / Baritone",
        "角色A音色": "温暖 / Warm", "角色A唱法": "流行/通俗 / Pop Vocal",
        "角色B配置": "女声 / Female Vocal", "角色B音区": "女高音 / Soprano",
        "角色B音色": "空灵 / Ethereal Airy", "角色B唱法": "流行/通俗 / Pop Vocal",
        "和声伴唱": "双声部和声 / Double-Tracked Harmonies",
        "人声效果": "暖混响 / Warm Reverb",
    },
    "🎭 男女对唱 + 史诗合唱 / Duet with Epic Choir": {
        "音乐风格": "[官方] 史诗 / Epic",
        "风格融合": "不指定 / Unspecified",
        "速度": "慢速 60-75 / Slow 60-75 BPM",
        "调号": "降B / B-flat",
        "调式": "大调 / Major",
        "拍号": "4/4",
        "情绪氛围": "庄严 / Solemn",
        "情绪演变": "由静到扬 / Gradual Rise",
        "使用场景": "黄昏 / Sunset",
        "段落结构": "标准流行 / Standard Pop",
        "制作质感": "大厅混响 / Hall Reverb",
        "主奏乐器": "弦乐组 / Strings",
        "辅助乐器": "法国号 / French Horn",
        "纯人声无伴奏": False,
        "合唱团": "大型混声合唱团 / Large Mixed SATB Choir",
        "角色分工": "A主歌B副歌 / A Verses B Chorus",
        "角色A配置": "女声 / Female Vocal", "角色A音区": "女高音 / Soprano",
        "角色A音色": "空灵 / Ethereal Airy", "角色A唱法": "美声 / Bel Canto",
        "角色B配置": "男声 / Male Vocal", "角色B音区": "男高音 / Tenor",
        "角色B音色": "浑厚 / Deep Rich", "角色B唱法": "美声 / Bel Canto",
        "和声伴唱": "多人叠唱 / Stacked Harmonies",
        "人声效果": "暖混响 / Warm Reverb",
    },
}

JZL_MiniMaxMusicCaptionDuet._RECIPES = {
    "自定义 / Custom": {},
    **{
        # 基础配方是单节点结构，剔除单人专属人声键（和声/效果两键双人共用，保留）
        label: {
            **{k: v for k, v in vals.items() if k not in _SINGLE_ONLY_VOCAL_KEYS},
            **_DUET_CAST.get(label, {}),
        }
        for label, vals in JZL_MiniMaxMusicCaption._RECIPES.items()
        if label != "自定义 / Custom"
    },
    **_DUET_ONLY_RECIPES,
}


# ═══════════════════════════════════════════════════════════
#  合并 music_styles.py 的结构化 vocal / arrangement
#  （global 仍由 _STYLES 提供，运行时按句拆成官方 4 子块）
# ═══════════════════════════════════════════════════════════
def _merge_structured_styles():
    """把 music_styles.py 的结构化 vocal / arrangement 合并进 _STYLES。"""
    styles = JZL_MiniMaxMusicCaption._STYLES
    missing = [name for name in styles if name not in MUSIC_STYLES]
    if missing:
        raise RuntimeError(f"music_styles.py 缺少风格定义: {missing}")
    for name, data in MUSIC_STYLES.items():
        target = styles.get(name)
        if target is not None:
            target["vocal"] = data["vocal"]
            target["arrangement"] = data["arrangement"]


_merge_structured_styles()
