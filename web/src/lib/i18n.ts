// UI chrome only. Every sentence ABOUT TAJWEED comes from the server, out of
// content/rules.json — never from here and never from an LLM.
//
// Uzbek uses the proper modifier letter ʻ (U+02BB) in oʻ / gʻ, not an
// apostrophe. Russian is written as Russian, not as a translation of the Uzbek.
// Both are first drafts by a developer and want a native pass before launch.
export type Lang = "uz" | "ru";

/**
 * Month names, written out rather than left to Intl.
 *
 * Chrome ships no CLDR month data for `uz-UZ`, so Intl.DateTimeFormat falls
 * back and renders the dateline as "M08 6, THU" — a placeholder month, in
 * English, in caps. Russian resolves fine, but formatting the two languages by
 * different mechanisms is how one of them silently regresses later, so both are
 * spelled out here.
 */
export const MONTHS: Record<Lang, string[]> = {
  uz: ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul",
       "avgust", "sentabr", "oktabr", "noyabr", "dekabr"],
  ru: ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
       "августа", "сентября", "октября", "ноября", "декабря"],
};

/** Today, as a dateline. No weekday, no clock — this is a date, not a timer. */
export function dateline(lang: Lang, d = new Date()): string {
  return `${d.getDate()} ${MONTHS[lang][d.getMonth()]}`;
}

const STRINGS = {
  uz: {
    // navigation
    nav_label: "Asosiy boʻlimlar",
    nav_today: "Bugun",
    nav_practice: "Mashq",
    nav_learn: "Oʻrganish",
    nav_memorize: "Yodlash",
    nav_profile: "Profil",
    nav_library: "Oyatlar",
    nav_log: "Yozuvlar",

    // ── onboarding. No sign up, no log in: there are no accounts, and the
    // consent step is the real decision being made here.
    onboard_welcome: "Tilawahga xush kelibsiz",
    onboard_welcome_body:
      "Qurʼonni ovoz chiqarib oʻqing, tajvid boʻyicha tinch va aniq izoh oling. Baho ham, reyting ham yoʻq — faqat siz va matn.",
    onboard_begin: "Boshlash",
    onboard_next: "Davom etish",
    onboard_skip: "Hozircha oʻtkazib yuborish",
    onboard_lang: "Qaysi tilda oʻqiymiz?",
    onboard_lang_body: "Izohlar va tarjimalar shu tilda koʻrsatiladi.",
    onboard_level: "Qurʼon oʻqishda tajribangiz qanday?",
    onboard_level_body:
      "Bu javob faqat bitta narsani belgilaydi: sizga qaysi qori ovozi taklif qilinishini. Istalgan vaqtda oʻzgartirasiz.",
    onboard_level_new: "Endi boshlayapman",
    onboard_level_new_note: "Har bir jumlani takrorlaydigan muallim qorisi",
    onboard_level_some: "Biroz oʻqiganman",
    onboard_level_some_note: "Odatdagi murattal oʻqish",
    onboard_level_fluent: "Erkin oʻqiyman",
    onboard_level_fluent_note: "Odatdagi murattal oʻqish",

    // ── today
    today_greeting: "Assalomu alaykum",
    today_continue: "Kaldirgan joyingiz",
    today_resume: "Shu oyatni oʻqish",
    today_progress: "{of} oyatdan {n}-si",
    today_recent: "Soʻnggi mashqlar",
    today_recent_none: "Hali mashq qilinmagan.",
    today_recent_off:
      "Yozuvlar saqlanmayapti. Profilda yoqsangiz, shu yerda koʻrinadi.",
    today_next: "Keyingisi",
    today_next_why: "Shu suradagi navbatdagi oyat",
    today_first_title: "Qaysi oyatdan boshlaymiz?",
    today_first_body:
      "Surani tanlang, oyatni oʻqing — keyingi safar aynan shu yerdan davom etasiz.",
    today_first_action: "Sura tanlash",

    // ── the dark recording card
    studio_ready: "Yozishga tayyor",
    studio_live: "Yozilmoqda",
    studio_thinking: "Tahlil qilinmoqda",
    studio_idle_primary: "Tugmani bosing",
    studio_idle_secondary: "Shoshilmang — vaqtingiz yetarli.",
    studio_live_secondary: "Tinch va sekin oʻqing. Tugatgach, toʻxtating.",
    studio_thinking_primary: "Oʻqishingiz tinglanmoqda",
    studio_thinking_secondary:
      "Bu 15–30 soniya davom etishi mumkin. Ilova qotib qolgani yoʻq.",
    studio_last: "Oxirgi mashq",
    studio_accuracy: "Aniqlik",

    // ── the two failures that are not the learner's fault
    // ── picker
    pick_sura_sub: "Surani tanlang, keyin oyatni.",
    group_short: "Qisqa suralar",
    group_medium: "Oʻrtacha suralar",
    group_long: "Uzun suralar",
    no_matches_body: "«{q}» boʻyicha hech narsa topilmadi. Sura nomini, raqamini yoki arabcha nomini yozib koʻring.",
    no_matches_clear: "Qidiruvni tozalash",
    sura_failed_title: "Surani yuklab boʻlmadi",
    sura_failed_body: "Aloqa uzildi shekilli. Internetni tekshirib, qayta urinib koʻring.",

    mic_denied_title: "Mikrofonga ruxsat berilmagan",
    mic_denied_body:
      "Brauzer mikrofonga kirishga ruxsat bermadi. Manzil satridagi qulf belgisini bosib, mikrofonni yoqing — soʻng qaytadan urinib koʻring.",
    // The recording survives the failure, so the retry costs the learner
    // nothing. That is the whole point of separating this from a generic error.
    net_failed_title: "Yuborib boʻlmadi",
    net_failed_body_kept:
      "Aloqa uzildi, lekin oʻqishingiz saqlanib qoldi. Qaytadan oʻqishingiz shart emas — shunchaki yana yuboring.",
    net_failed_body:
      "Aloqa uzildi va yozuv saqlanmadi. Internetni tekshirib, qaytadan oʻqing.",
    net_failed_resend: "Yozuvni qayta yuborish",

    // ── learn / memorize. Nothing is invented: no courses, no instructors,
    // no zeroed progress rings.
    learn_title: "Darslar hali tayyor emas",
    learn_body:
      "Tajvid darslari ustida ishlanmoqda. Tayyor boʻlmaguncha bu yerda hech narsa koʻrsatmaymiz.",
    learn_note:
      "Har bir dars matni qori tomonidan tekshirilgandan keyingina qoʻshiladi.",
    memorize_title: "Yodlash rejasi hali tayyor emas",
    memorize_body:
      "Takrorlash jadvali va yodlash rejasi ustida ishlanmoqda. Soxta jadval koʻrsatgandan koʻra, boʻsh qoldirganimiz maʼqul.",
    memorize_note:
      "Tayyor boʻlgach, u sizning haqiqiy mashqlaringizga asoslanadi.",

    // ── profile
    profile_initials: "﷽",
    profile_name: "Sizning mashqlaringiz",
    profile_sub: "Hisob yoʻq — hammasi shu qurilmada saqlanadi.",
    profile_history: "Tarix",
    profile_all: "Barchasi",
    profile_settings: "Sozlamalar",
    profile_lang: "Til",
    profile_reciter_help: "Tinglash uchun ovoz",
    profile_script: "Mushaf turi",
    profile_script_help:
      "Baholash Usmoniy yozuvga asoslanadi. Boshqa yozuv turlari hali qoʻshilmagan.",
    profile_script_value: "Madina (Usmoniy)",
    profile_advanced: "Qoʻshimcha tajvid sozlamalari",
    profile_advanced_body:
      "Hozircha sozlanadigan narsa yoʻq. Aniqlik chegaralari haqiqiy oʻqishlar toʻplangandan keyin ochiladi.",
    profile_data: "Maʼlumotlaringiz",
    profile_delete: "Barcha maʼlumotlarimni oʻchirish",
    profile_delete_help:
      "Yozuvlaringiz serverdan butunlay oʻchiriladi. Buni qaytarib boʻlmaydi.",
    profile_off_title: "Yozuvlar saqlanmayapti",
    profile_off_body:
      "Siz tarixni saqlashga rozilik bermagansiz. Bu toʻliq oʻz ixtiyoringiz — quyidan istalgan vaqtda yoqishingiz mumkin.",
    profile_empty_title: "Hali yozuv yoʻq",
    profile_empty_body: "Birinchi oyatni oʻqing — u shu yerda paydo boʻladi.",

    // recitation
    listen: "Qori oʻqishini tinglang",
    record: "Oʻqishni boshlash",
    stop: "Toʻxtatish",
    recording_hint: "Shoshilmang. Tinch va sekin oʻqing.",
    waiting: "Tinglanmoqda",
    waiting_hint: "Bir necha soniya kutib turing.",

    // ── the outcome statement. One sentence, no score, no badge.
    verdict_title: "Koʻrib chiqadigan {n} ta joy bor",
    verdict_body:
      "Har biri uchun nima boʻlgani va qanday tuzatish kerakligi quyida yozilgan. Shoshilmang — bittadan.",
    verdict_all_fixed: "Hammasi tuzatildi",
    verdict_all_fixed_body: "Endi oyatni boshidan bir marta oʻqib koʻring.",
    verdict_again: "Oyatni qaytadan oʻqish",

    // all clear
    clear_title: "Barakalla",
    clear_body: "Bu oʻqishda xatolik topilmadi.",

    // The model returned nothing analysable — no judgement was formed at all.
    // This sentence means EXACTLY that and must never be reused for a
    // correction that exists but is being withheld; see withheld_* below.
    unsure_title: "Toʻliq baholay olmadik",
    unsure_body:
      "Bu oʻqishni ishonch bilan baholash uchun maʼlumot yetarli boʻlmadi. Ustozingiz bilan birga tekshirib koʻring.",

    // A judgement WAS formed and the review gate withheld it. Different cause,
    // different sentence — the learner should know something was noticed.
    withheld_title: "Izoh hali tayyor emas",
    withheld_body:
      "Oʻqishingizda eʼtibor beriladigan joy topildi, lekin uning izohini qori hali tasdiqlamagan. Shuning uchun koʻrsatmayapmiz. Ustozingiz bilan tekshirib koʻring.",

    // retry
    retry_noisy_title: "Atrof shovqinli",
    retry_noisy_body:
      "Yozuvda tashqi shovqin koʻp boʻlgani uchun oʻqishni aniq eshita olmadik.",
    retry_short_title: "Yozuv juda qisqa",
    retry_short_body: "Oyat toʻliq oʻqilmagan koʻrinadi.",
    retry_long_title: "Yozuv juda uzun",
    retry_long_body: "Faqat shu oyatni oʻqing, keyingisiga oʻtmang.",
    retry_quiet_title: "Ovoz eshitilmadi",
    retry_quiet_body:
      "Yozuvda deyarli ovoz yoʻq. Mikrofonga ruxsat berilganini tekshiring.",
    retry_toolong_title: "Bu oyat bir oʻqishda juda uzun",
    retry_toolong_body:
      "Bu oyatni toʻliq baholay olmaymiz — u juda uzun. Quyidagi «Oyatning bir qismini mashq qilish» orqali qismlarga boʻlib oʻqing.",
    // Shown BEFORE recording, so nobody waits several minutes to be told this.
    too_long_hint:
      "Bu oyat toʻliq baholash uchun juda uzun. Uni qismlarga boʻlib mashq qiling.",
    retry_unclear_title: "Oʻqishni aniq eshita olmadik",
    retry_unclear_body:
      "Oyat toʻliq va tinch oʻqilsa, bahomiz ancha aniq boʻladi. Shoshilmasdan qaytadan oʻqing.",
    retry_tip_full: "Oyatni boshidan oxirigacha oʻqing",
    retry_tip_pause: "Yozishni boshlagach, bir lahza kutib, keyin oʻqing",
    retry_tip_room: "Tinchroq xonaga oʻting",
    retry_tip_close: "Telefonni ogʻzingizga yaqinroq tuting",
    retry_tip_wait: "Deraza yoki fen ovozi tinganini kuting",
    retry_again: "Qayta oʻqish",

    // ── card titles. The learner-facing name of each error category.
    // These replace the internal codes (LETTER_ADDED, GENERIC_SIFAT_MISMATCH)
    // which must never appear on screen. Keyed by TajweedError.kind.
    kind_extra_letter: "Ortiqcha harf",
    kind_missing_letter: "Tushib qolgan harf",
    kind_wrong_letter: "Notoʻgʻri harf",
    kind_pronunciation: "Talaffuz",
    kind_tajweed: "Tajvid",
    kind_madd: "Mad",
    kind_ghunna: "Gʻunna",
    kind_haraka: "Harakat",
    // Length on a DOUBLED CONSONANT, not on a madd letter. Its own title
    // because it is its own ruling — see cards.SHADDA.
    kind_shadda: "Tashdid",

    // correction card
    label_heard: "Nimani eshitdik",
    label_fix: "Qanday tuzatish kerak",
    // The EIGHT card slots, in reading order: the error, the rule name, where
    // it happened, what happened, how to fix it, then listen / practise /
    // re-check inside the ladder.
    card_where: "Qayerda",
    card_you_said: "Siz aytdingiz",
    card_correct: "Toʻgʻrisi",
    card_fix: "Tuzatish",
    card_practice: "Endi mashq qilamiz",
    // Repeats are merged into one card; this says how many and where.
    card_times: "marta uchradi",
    // WHICH instance of the letter, when the word holds more than one.
    // {n} of {of}: "soʻzdagi 2-chi" — shown only when there is a choice.
    which_letter: "Soʻzdagi {n}-chi (jami {of}):",

    // ── listening. Every rung that HAS a recording offers both speeds; a rung
    // with none offers no button at all rather than one that plays nothing.
    listen_letter: "Harf tovushini eshitish",
    listen_ayah: "Oyatni qori oʻqishida eshitish",
    listen_normal: "Eshitish",
    listen_slow: "Sekin eshitish",

    // ── the duration meter. Length drawn as length, because "2 oʻrniga 6" is a
    // number the learner has to convert into a duration — and duration is the
    // thing they got wrong.
    harakat: "harakat",
    meter_needed: "Kerak",
    meter_yours: "Siz",
    meter_count_with_me: "Men bilan sanang:",

    // ── the practice ladder. Narrow to wide: the letter alone, the letter
    // with each haraka, the word they misread, then back to the ayah.
    rung_letter: "Faqat shu harf",
    rung_syllables: "Harakatlar bilan",
    rung_word: "Shu soʻz",
    rung_ayah: "Endi oyatni oʻqing",
    rung_record: "Oʻqib koʻrish",
    rung_again: "Yana bir bor",
    // Rungs the engine cannot score. Says what to do instead of leaving the
    // rung looking as though its button failed to load.
    rung_say: "Ovoz chiqarib ayting",
    // A rung the learner confirms themselves. Phrased as a statement they make,
    // NOT as a result we measured — the engine has no target for a bare letter
    // and must not imply it judged one.
    rung_said: "Aytdim",
    rung_said_again: "Yana aytdim",
    rung_done: "Bajarildi",
    // Rungs above the one in play. The ladder is an order, and jumping to the
    // ayah is doing the test again rather than the practice.
    rung_locked: "Avvalgi bosqichni bajaring",
    rung_need: "kerak:",

    // ── the recovery loop
    retry_word: "Qayta urinish",
    retry_word_hint: "Faqat shu soʻzni oʻqing.",
    retry_word_stop: "Toʻxtatish",
    retry_checking: "Tekshirilmoqda",
    fixed_title: "Barakalla! Toʻgʻirladingiz.",
    // Shown when the re-read still has the same mistake. No scolding: the same
    // card comes back unchanged and this is the whole message.
    not_yet: "Hali ham shu joyda. Yana bir bor urinib koʻring.",
    // Playback of the learner's own recording, so they can judge for themselves
    // whether a flagged error is real.
    hear_yourself: "Oʻz oʻqishingizni eshitish",
    hear_yourself_stop: "Toʻxtatish",
    // Shown when no entry exists for a detected code: the location is all we
    // can honestly state, and stating it beats saying nothing.
    located_unknown: "Xato joyi aniqlanmadi.",
    teacher_note: "Bunga ishonchimiz toʻliq emas — ustozingiz bilan tekshiring.",
    wrong_button: "Bu baho notoʻgʻri",
    wrong_thanks: "Rahmat. Buni koʻrib chiqamiz.",

    // Draft corrections — the normal state outside production, where the gate
    // is open by default and every unreviewed card carries a marker.
    draft_chip: "QORALAMA",
    draft_note: "Bu izohni qori tekshirmagan. Faqat sinov uchun.",
    // Ends where it ends. It used to finish "Faqat kod:" — "only the code:" —
    // and then print no code, because printing one is forbidden. A sentence
    // promising an identifier the UI must never show was a leftover from when
    // it did.
    draft_unauthored:
      "Bu xato uchun izoh hali yozilmagan. Joyini koʻrsatamiz, xolos.",
    draft_banner_title: "Tekshirilmagan izohlar koʻrsatilmoqda",
    draft_banner_body:
      "Sinov rejimi: aniqlangan barcha xatolar koʻrsatilmoqda, jumladan qori hali tekshirmaganlari ham. Har biri QORALAMA deb belgilangan.",

    // picker — the whole Quran, not a shortlist
    pick_sura: "Sura tanlang",
    search_sura: "Sura nomi yoki raqami",
    no_matches: "Hech narsa topilmadi.",
    pick_ayah: "Oyatni tanlang.",
    // Narrowing to part of an ayah is offered inside Recite, as a choice —
    // never as a question the picker forces before you can start.
    practise_part: "Oyatning bir qismini mashq qilish",
    practise_whole: "Butun oyatni oʻqish",
    ayat_count: "oyat",

    // reading
    read_mode: "Oʻqish koʻrinishi",
    mode_mushaf: "Mushaf",
    mode_verse: "Oyatma-oyat",
    mushaf_hint: "Mashq qilish uchun oyatni bosing.",
    prev_ayah: "Oldingi oyat",
    next_ayah: "Keyingi oyat",
    practise_this: "Shu oyatni mashq qilish",
    no_translation: "Bu oyat uchun tarjima topilmadi.",
    pause: "Toʻxtatish",

    // reciters
    reciter: "Qori",
    style_muallim: "Muallim (takrorlab oʻrgatadi)",
    style_murattal: "Murattal",
    style_mujawwad: "Mujavvad",
    parts: "qism",
    words: "soʻz",
    seconds_short: "s",
    estimate: "Taxminiy davomiylik",
    change_selection: "Boshqa oyat tanlash",

    // library
    library_title: "Oyatlar",
    library_sub: "Mashq qilish uchun oyatni tanlang.",
    level: "Daraja",

    // log
    log_title: "Yozuvlar",
    log_sub: "Oxirgi oʻqishlaringiz.",
    log_empty: "Hali oʻqish yozilmagan.",
    log_clear: "Xatoliksiz",
    log_noted: "Izoh bor",
    log_unassessed: "Baholanmadi",
    log_retry: "Qayta yozilgan",

    // pilot banner
    pilot_title: "Sinov versiyasi",
    pilot_body:
      "Bu dastur hali sinovdan oʻtmoqda. Tajweed boʻyicha izohlar toʻliq tasdiqlanmagan — ustozingiz bilan tekshirib boring.",

    // consent
    consent_title: "Maʼlumotlaringiz",
    consent_body:
      "Oʻqishlaringizni saqlashga ruxsat bersangiz, tarixni koʻrasiz va biz baholash sifatini yaxshilaymiz. Istagan vaqtda oʻchirib tashlashingiz mumkin.",
    consent_toggle: "Oʻqishlarimni saqlashga ruxsat beraman",
    consent_delete: "Barcha maʼlumotlarim oʻchirildi.",

    // first-run consent screen
    consent_gate_title: "Maʼlumotlaringiz sizniki",
    consent_gate_intro:
      "Boshlashdan oldin bir narsani aniq qilib olaylik: nimani saqlashimizni siz hal qilasiz. Hech narsa avtomatik saqlanmaydi.",
    consent_gate_none_title: "Hech narsa saqlanmaydi",
    consent_gate_none_body:
      "Ruxsat bermasangiz, oʻqishingiz baholanadi va darhol unutiladi. Dasturdan toʻliq foydalanaveramiz.",
    consent_attempts_label: "Oʻqishlarim tarixini saqlash",
    consent_attempts_help:
      "Qaysi oyatni oʻqiganingiz va qanday izoh olganingiz saqlanadi. Ovozingiz saqlanmaydi.",
    consent_audio_label: "Ovoz yozuvlarimni saqlash",
    consent_audio_help:
      "Ovozingiz saqlanadi va faqat baholash sifatini yaxshilash uchun ishlatiladi. Bu alohida ruxsat — istamasangiz belgilamang.",
    consent_gate_accept: "Davom etish",
    consent_gate_skip: "Hech narsa saqlamasdan davom etish",
    consent_gate_footer:
      "Fikringizni istagan vaqtda «Yozuvlar» boʻlimida oʻzgartirishingiz mumkin. Oʻchirsangiz, saqlangan hamma narsa haqiqatan oʻchiriladi.",

    // The connected API is older than this build and does not send fields the
    // cards require. Developer-facing on purpose: a learner never sees this
    // unless a deploy went wrong, and vagueness here costs hours.
    api_stale_title: "Server eskirgan",
    api_stale_body:
      "Ulangan API bu versiya talab qiladigan maydonlarni yubormayapti. Serverni qayta ishga tushiring. Yetishmayotgan maydonlar:",

    // Rendering failed for one card / for the results view. Not a tajweed
    // statement and not an assessment - it says the app broke, not the
    // recitation. Deliberately plain: a learner cannot act on a stack trace.
    card_broken: "Bu izohni koʻrsatib boʻlmadi.",
    results_broken: "Natijalarni koʻrsatishda xatolik yuz berdi. Oʻqishingiz saqlandi.",

    // generic
    error_generic: "Xatolik yuz berdi. Qayta urinib koʻring.",
    loading: "Yuklanmoqda",
  },

  ru: {
    nav_label: "Основные разделы",
    nav_today: "Сегодня",
    nav_practice: "Практика",
    nav_learn: "Обучение",
    nav_memorize: "Заучивание",
    nav_profile: "Профиль",
    nav_library: "Аяты",
    nav_log: "Записи",

    onboard_welcome: "Добро пожаловать в Tilawah",
    onboard_welcome_body:
      "Читайте Коран вслух и получайте спокойный, точный разбор по таджвиду. Ни оценок, ни рейтингов — только вы и текст.",
    onboard_begin: "Начать",
    onboard_next: "Далее",
    onboard_skip: "Пропустить пока",
    onboard_lang: "На каком языке читаем?",
    onboard_lang_body: "На нём будут показаны пояснения и переводы.",
    onboard_level: "Каков ваш опыт чтения Корана?",
    onboard_level_body:
      "Ответ определяет ровно одно: какой чтец предлагается по умолчанию. Изменить можно в любой момент.",
    onboard_level_new: "Только начинаю",
    onboard_level_new_note: "Муаллим — повторяет каждую фразу",
    onboard_level_some: "Немного читал",
    onboard_level_some_note: "Обычное чтение мураттал",
    onboard_level_fluent: "Читаю свободно",
    onboard_level_fluent_note: "Обычное чтение мураттал",

    today_greeting: "Ассаламу алайкум",
    today_continue: "Вы остановились здесь",
    today_resume: "Читать этот аят",
    today_progress: "{n}-й из {of} аятов",
    today_recent: "Недавняя практика",
    today_recent_none: "Пока ничего не прочитано.",
    today_recent_off:
      "Записи не сохраняются. Включите в профиле — и они появятся здесь.",
    today_next: "Следующее",
    today_next_why: "Следующий аят этой суры",
    today_first_title: "С какого аята начнём?",
    today_first_body:
      "Выберите суру и прочитайте аят — в следующий раз продолжите отсюда.",
    today_first_action: "Выбрать суру",

    studio_ready: "Готово к записи",
    studio_live: "Идёт запись",
    studio_thinking: "Идёт разбор",
    studio_idle_primary: "Нажмите кнопку",
    studio_idle_secondary: "Не торопитесь — времени достаточно.",
    studio_live_secondary: "Читайте спокойно. Закончив, остановите запись.",
    studio_thinking_primary: "Слушаем ваше чтение",
    studio_thinking_secondary:
      "Это может занять 15–30 секунд. Приложение не зависло.",
    studio_last: "Прошлая практика",
    studio_accuracy: "Точность",

    pick_sura_sub: "Выберите суру, затем аят.",
    group_short: "Короткие суры",
    group_medium: "Средние суры",
    group_long: "Длинные суры",
    no_matches_body: "По запросу «{q}» ничего не найдено. Попробуйте название суры, её номер или арабское имя.",
    no_matches_clear: "Очистить поиск",
    sura_failed_title: "Не удалось загрузить суру",
    sura_failed_body: "Похоже, связь прервалась. Проверьте интернет и попробуйте снова.",

    mic_denied_title: "Нет доступа к микрофону",
    mic_denied_body:
      "Браузер не дал доступ к микрофону. Нажмите значок замка в адресной строке, включите микрофон и попробуйте снова.",
    net_failed_title: "Не удалось отправить",
    net_failed_body_kept:
      "Связь прервалась, но ваше чтение сохранилось. Перечитывать не нужно — просто отправьте ещё раз.",
    net_failed_body:
      "Связь прервалась, и запись не сохранилась. Проверьте интернет и прочитайте заново.",
    net_failed_resend: "Отправить запись снова",

    learn_title: "Уроки ещё не готовы",
    learn_body:
      "Уроки по таджвиду в работе. Пока они не готовы, мы не показываем здесь ничего.",
    learn_note:
      "Каждый урок появится только после проверки текста чтецом-кари.",
    memorize_title: "План заучивания ещё не готов",
    memorize_body:
      "График повторений в работе. Лучше оставить раздел пустым, чем показать выдуманное расписание.",
    memorize_note:
      "Когда он появится, он будет опираться на вашу реальную практику.",

    profile_initials: "﷽",
    profile_name: "Ваша практика",
    profile_sub: "Аккаунта нет — всё хранится на этом устройстве.",
    profile_history: "История",
    profile_all: "Все",
    profile_settings: "Настройки",
    profile_lang: "Язык",
    profile_reciter_help: "Голос для прослушивания",
    profile_script: "Тип мусхафа",
    profile_script_help:
      "Разбор опирается на османское письмо. Другие начертания пока не добавлены.",
    profile_script_value: "Медина (Османский)",
    profile_advanced: "Дополнительные настройки таджвида",
    profile_advanced_body:
      "Настраивать пока нечего. Пороги точности откроются после сбора реальных чтений.",
    profile_data: "Ваши данные",
    profile_delete: "Удалить все мои данные",
    profile_delete_help:
      "Ваши записи будут полностью удалены с сервера. Это необратимо.",
    profile_off_title: "Записи не сохраняются",
    profile_off_body:
      "Вы не давали согласия на хранение истории. Это ваш выбор — включить можно ниже в любой момент.",
    profile_empty_title: "Записей пока нет",
    profile_empty_body: "Прочитайте первый аят — он появится здесь.",

    listen: "Послушайте чтеца",
    record: "Начать чтение",
    stop: "Остановить",
    recording_hint: "Не торопитесь. Читайте спокойно.",
    waiting: "Слушаем",
    waiting_hint: "Это займёт несколько секунд.",

    verdict_title: "Есть {n} мест(а) для разбора",
    verdict_body:
      "Ниже для каждого написано, что произошло и как это исправить. Не торопитесь — по одному.",
    verdict_all_fixed: "Всё исправлено",
    verdict_all_fixed_body: "Теперь прочитайте аят целиком ещё раз.",
    verdict_again: "Прочитать аят снова",

    clear_title: "Прекрасно",
    clear_body: "В этом чтении ошибок не найдено.",

    unsure_title: "Не смогли оценить полностью",
    unsure_body:
      "Данных не хватило, чтобы оценить это чтение уверенно. Проверьте вместе с вашим устозом.",

    withheld_title: "Замечание пока не готово",
    withheld_body:
      "В вашем чтении есть на что обратить внимание, но пояснение к этому ещё не подтверждено чтецом, поэтому мы его не показываем. Проверьте с вашим устозом.",

    retry_noisy_title: "Вокруг шумно",
    retry_noisy_body:
      "В записи много постороннего шума, и мы не расслышали чтение отчётливо.",
    retry_short_title: "Запись слишком короткая",
    retry_short_body: "Похоже, аят прочитан не полностью.",
    retry_long_title: "Запись слишком длинная",
    retry_long_body: "Прочитайте только этот аят, не переходя к следующему.",
    retry_quiet_title: "Звук не слышен",
    retry_quiet_body:
      "В записи почти нет звука. Проверьте, разрешён ли доступ к микрофону.",
    retry_toolong_title: "Этот аят слишком длинный для одного чтения",
    retry_toolong_body:
      "Мы не можем оценить этот аят целиком — он слишком длинный. Прочитайте его по частям через «Потренировать часть аята» ниже.",
    too_long_hint:
      "Этот аят слишком длинный, чтобы оценить его целиком. Потренируйте его по частям.",
    retry_unclear_title: "Не расслышали чтение отчётливо",
    retry_unclear_body:
      "Если прочитать аят полностью и спокойно, оценка будет намного точнее. Не торопитесь и прочитайте ещё раз.",
    retry_tip_full: "Прочитайте аят от начала до конца",
    retry_tip_pause: "Начав запись, выждите мгновение и затем читайте",
    retry_tip_room: "Перейдите в тихую комнату",
    retry_tip_close: "Держите телефон ближе ко рту",
    retry_tip_wait: "Дождитесь, пока стихнет шум за окном",
    retry_again: "Прочитать снова",

    kind_extra_letter: "Лишняя буква",
    kind_missing_letter: "Пропущенная буква",
    kind_wrong_letter: "Неверная буква",
    kind_pronunciation: "Произношение",
    kind_tajweed: "Таджвид",
    kind_madd: "Мадд",
    kind_ghunna: "Гунна",
    kind_haraka: "Огласовка",
    kind_shadda: "Ташдид",

    label_heard: "Что мы услышали",
    label_fix: "Как исправить",
    card_where: "Где",
    card_you_said: "Вы сказали",
    card_correct: "Правильно",
    card_fix: "Исправление",
    card_practice: "Теперь потренируемся",
    card_times: "раза встретилось",
    which_letter: "{n}-я в слове (всего {of}):",

    listen_letter: "Послушать звук буквы",
    listen_ayah: "Послушать аят у чтеца",
    listen_normal: "Послушать",
    listen_slow: "Медленно",

    harakat: "хараки",
    meter_needed: "Нужно",
    meter_yours: "У вас",
    meter_count_with_me: "Считайте со мной:",

    rung_letter: "Только эта буква",
    rung_syllables: "С огласовками",
    rung_word: "Это слово",
    rung_ayah: "Теперь весь аят",
    rung_record: "Прочитать",
    rung_again: "Ещё раз",
    rung_say: "Скажите вслух",
    rung_said: "Сказал",
    rung_said_again: "Сказал ещё раз",
    rung_done: "Выполнено",
    rung_locked: "Сначала пройдите предыдущий шаг",
    rung_need: "нужно:",

    retry_word: "Попробовать снова",
    retry_word_hint: "Прочитайте только это слово.",
    retry_word_stop: "Остановить",
    retry_checking: "Проверяем",
    fixed_title: "Прекрасно! Вы исправили.",
    not_yet: "Пока то же место. Попробуйте ещё раз.",
    hear_yourself: "Послушать своё чтение",
    hear_yourself_stop: "Остановить",
    located_unknown: "Место ошибки не определено.",
    teacher_note: "Мы не вполне уверены — проверьте с вашим устозом.",
    wrong_button: "Оценка неверна",
    wrong_thanks: "Спасибо. Мы это разберём.",

    draft_chip: "ЧЕРНОВИК",
    draft_note: "Это замечание не проверено чтецом. Только для тестирования.",
    draft_unauthored:
      "Для этой ошибки пояснение ещё не написано. Показываем только место.",
    draft_banner_title: "Показываются непроверенные замечания",
    draft_banner_body:
      "Тестовый режим: показываются все найденные ошибки, включая ещё не проверенные чтецом. Каждая помечена как ЧЕРНОВИК.",

    pick_sura: "Выберите суру",
    search_sura: "Название или номер суры",
    no_matches: "Ничего не найдено.",
    pick_ayah: "Выберите аят.",
    practise_part: "Потренировать часть аята",
    practise_whole: "Читать аят целиком",
    ayat_count: "аятов",

    read_mode: "Режим чтения",
    mode_mushaf: "Мусхаф",
    mode_verse: "По аятам",
    mushaf_hint: "Нажмите на аят, чтобы потренировать его.",
    prev_ayah: "Предыдущий аят",
    next_ayah: "Следующий аят",
    practise_this: "Потренировать этот аят",
    no_translation: "Перевод для этого аята не найден.",
    pause: "Пауза",

    reciter: "Чтец",
    style_muallim: "Муаллим (обучающее чтение)",
    style_murattal: "Мураттал",
    style_mujawwad: "Муджаввад",
    parts: "частей",
    words: "слова",
    seconds_short: "с",
    estimate: "Примерная длительность",
    change_selection: "Выбрать другой аят",

    library_title: "Аяты",
    library_sub: "Выберите аят для практики.",
    level: "Уровень",

    log_title: "Записи",
    log_sub: "Ваши последние чтения.",
    log_empty: "Пока нет записанных чтений.",
    log_clear: "Без ошибок",
    log_noted: "Есть замечание",
    log_unassessed: "Не оценено",
    log_retry: "Перезаписано",

    pilot_title: "Пробная версия",
    pilot_body:
      "Приложение ещё тестируется. Замечания по таджвиду пока не полностью выверены — сверяйтесь с вашим устозом.",

    consent_title: "Ваши данные",
    consent_body:
      "Если разрешите сохранять чтения, вы увидите историю, а мы улучшим качество оценки. Удалить можно в любой момент.",
    consent_toggle: "Разрешаю сохранять мои чтения",
    consent_delete: "Все ваши данные удалены.",

    consent_gate_title: "Ваши данные принадлежат вам",
    consent_gate_intro:
      "Прежде чем начать, договоримся: вы решаете, что сохранять. По умолчанию не сохраняется ничего.",
    consent_gate_none_title: "Ничего не сохраняется",
    consent_gate_none_body:
      "Без разрешения чтение будет оценено и сразу забыто. Приложением можно пользоваться полностью.",
    consent_attempts_label: "Сохранять историю моих чтений",
    consent_attempts_help:
      "Сохраняется, какой аят вы читали и какое замечание получили. Голос не сохраняется.",
    consent_audio_label: "Сохранять мои голосовые записи",
    consent_audio_help:
      "Голос сохраняется и используется только для улучшения качества оценки. Это отдельное разрешение — не отмечайте, если не хотите.",
    consent_gate_accept: "Продолжить",
    consent_gate_skip: "Продолжить, ничего не сохраняя",
    consent_gate_footer:
      "Решение можно изменить в разделе «Записи» в любой момент. При отзыве всё сохранённое действительно удаляется.",

    api_stale_title: "Сервер устарел",
    api_stale_body:
      "Подключённый API не отправляет поля, которые нужны карточкам. Перезапустите сервер. Отсутствующие поля:",

    card_broken: "Не удалось показать это замечание.",
    results_broken: "Не удалось показать результаты. Ваше чтение сохранено.",

    error_generic: "Произошла ошибка. Попробуйте ещё раз.",
    loading: "Загрузка",
  },
} as const;

export type Key = keyof (typeof STRINGS)["uz"];

export function t(lang: Lang, key: Key): string {
  return STRINGS[lang][key];
}

export function retryCopy(lang: Lang, reason: string) {
  if (reason === "too_short")
    return {
      title: t(lang, "retry_short_title"),
      body: t(lang, "retry_short_body"),
      tips: [] as string[],
    };
  if (reason === "too_long")
    return {
      title: t(lang, "retry_long_title"),
      body: t(lang, "retry_long_body"),
      tips: [] as string[],
    };
  // Not the learner's doing: the ayah itself exceeds what the engine can hold
  // in memory. Says so, and points at the control that solves it.
  if (reason === "too_long_for_engine")
    return {
      title: t(lang, "retry_toolong_title"),
      body: t(lang, "retry_toolong_body"),
      tips: [] as string[],
    };
  if (reason === "too_quiet")
    return {
      title: t(lang, "retry_quiet_title"),
      body: t(lang, "retry_quiet_body"),
      tips: [t(lang, "retry_tip_close")],
    };
  // The model returned huruf muqatta'at — it could not resolve the recitation.
  // Usually a truncated take, so lead with reciting the ayah in full.
  if (reason === "unclear_recitation")
    return {
      title: t(lang, "retry_unclear_title"),
      body: t(lang, "retry_unclear_body"),
      tips: [
        t(lang, "retry_tip_full"),
        t(lang, "retry_tip_pause"),
        t(lang, "retry_tip_room"),
      ],
    };
  return {
    title: t(lang, "retry_noisy_title"),
    body: t(lang, "retry_noisy_body"),
    tips: [
      t(lang, "retry_tip_room"),
      t(lang, "retry_tip_close"),
      t(lang, "retry_tip_wait"),
    ],
  };
}
