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

/**
 * The greeting on Home, by hour of the local day.
 *
 * FIVE BANDS, NOT THREE, and the extra two are the point. A generic
 * morning/afternoon/evening split says nothing a clock does not; these are cut
 * where the day is actually cut for someone praying through it — the hour
 * around Bomdod gets "Tong muborak" rather than a flat "good morning", and the
 * late band after ʿIshāʾ is named as night rather than as evening.
 *
 * Deliberately NOT computed from prayer times. Those vary by city and by
 * method, the app does not know the learner's location, and a greeting that
 * claims to know when Bomdod is would be wrong for most people most days. The
 * hours below are an honest approximation and nothing more.
 */
export function greeting(lang: Lang, now = new Date()): string {
  const h = now.getHours();
  if (h < 6) return t(lang, "greet_dawn");
  if (h < 11) return t(lang, "greet_morning");
  if (h < 17) return t(lang, "greet_afternoon");
  if (h < 21) return t(lang, "greet_evening");
  return t(lang, "greet_night");
}

/**
 * "Last practiced N ago", from a real timestamp.
 *
 * Coarse on purpose — hours, then days — because the point is orientation, not
 * precision. "43 minutes ago" invites the learner to read a schedule into it.
 * Callers pass a real Date or do not call this at all: there is no "a while
 * ago" fallback, because a fallback is where an invented recency would live.
 */
export function sinceLabel(lang: Lang, then: Date, now = new Date()): string {
  const mins = Math.max(0, Math.round((now.getTime() - then.getTime()) / 60000));
  if (mins < 60) return t(lang, "since_recent");
  const hours = Math.round(mins / 60);
  if (hours < 24) {
    return t(lang, "since_hours").replace("{n}", String(hours));
  }
  return t(lang, "since_days").replace("{n}", String(Math.round(hours / 24)));
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
    nav_bookmark: "Saqlangan joy",
    // -- the entry experience --------------------------------------------
    welcome_1_title: "Qur'on yo'lingiz — yo'lboshchi bilan",
    welcome_1_body:
      "{brand} sizga nimadan boshlashni va keyin nima qilishni aytadi. O'zingiz reja tuzishingiz shart emas.",
    welcome_2_title: "O'qing — biz tinglaymiz",
    welcome_2_body:
      "Oyatni ovoz chiqarib o'qing. {brand} qaysi harfda, qaysi so'zda xato bo'lganini aniq ko'rsatadi va qanday tuzatishni tushuntiradi.",
    welcome_3_title: "Har kuni bir oz",
    welcome_3_body:
      "Kuniga bir necha daqiqa. Baho ham, reyting ham, musobaqa ham yo'q — faqat siz va matn.",
    welcome_start: "Boshlaymiz",
    onboard_choose_later: "Keyinroq tanlayman",
    personalize_done: "Tayyor",

    q_goal: "{brand}ga nima uchun keldingiz?",
    q_stage: "Qur'on yo'lingizda qayerdasiz?",
    q_focus: "Avval nimaga e'tibor beramiz?",
    q_minutes: "Kuniga qancha vaqt ajrata olasiz?",
    q_when: "Qachon mashq qilishni istaysiz?",

    goal_recitation: "O'qishimni yaxshilash",
    goal_tajweed: "Tajvidni o'rganish",
    goal_memorize: "Qur'onni yodlash",
    goal_habit: "Kundalik odat qilish",
    goal_understand: "Qur'onni ko'proq tushunish",
    goal_everything: "Hammasidan bir oz",

    stage_beginning: "Endi boshlayapman",
    stage_improving: "O'qiyman, lekin yaxshilamoqchiman",
    stage_comfortable: "O'qishim ancha ravon",
    stage_memorizing: "Hozir yodlayapman",

    focus_recitation: "O'qish",
    focus_tajweed: "Tajvid",
    focus_memorization: "Yodlash",
    focus_consistency: "Doimiylik",
    focus_understanding: "Tushunish",

    min_5: "5 daqiqa",
    min_10: "10 daqiqa",
    min_15: "15 daqiqa",
    min_20: "20 daqiqa",
    min_30: "30+ daqiqa",

    when_after_fajr: "Bomdoddan keyin",
    when_morning: "Ertalab",
    when_afternoon: "Kunduzi",
    when_after_maghrib: "Shomdan keyin",
    when_evening: "Kechqurun",
    when_later: "O'zim tanlayman",

    journey_mine: "MENING YO'LIM",
    journey_goal: "Maqsad",
    journey_daily: "Kunlik vaqt",
    journey_focus: "Yo'nalish",
    journey_when: "Mashq vaqti",
    journey_stage: "Daraja",
    journey_weekly: "Haftalik niyat",
    journey_build_title: "Keling, yo'lingizni tuzamiz.",
    journey_build_body: "Javoblaringiz asosida. Keyin istalgan vaqtda o'zgartirasiz.",
    journey_create_cta: "Yo'limni yaratish",
    journey_change: "Javoblarni o'zgartirish",
    journey_ready_title: "Yo'lingiz tayyor.",
    journey_today: "BUGUN",
    journey_this_week: "SHU HAFTA",
    journey_path: "HOZIRGI YO'NALISH",
    journey_begin_cta: "Bugungi yo'lni boshlash",
    minutes_n: "{n} daqiqa",
    minutes_per_day: "kuniga {n} daqiqa",
    sessions_n: "{n} marta",
    path_unset: "Hali tanlanmagan",
    step_practice: "Mashq",
    step_practice_note: "Oyat o'qing, tajvid bo'yicha izoh oling",
    step_reflect: "Tafakkur",
    step_reflect_note: "Kun hadisi",

    // -- achievements -----------------------------------------------------
    ach_recent: "SO'NGGI YUTUQLAR",
    ach_view_all: "Barchasi →",
    ach_all: "YUTUQLAR",
    ach_count: "{of} tadan {n} tasi",
    ach_not_built:
      "Bu bo'lim hali tayyor emas — hozircha bu yutuqni olib bo'lmaydi.",
    ach_first_step: "Birinchi qadam",
    ach_first_step_how: "Yo'lingizni yarating",
    ach_first_voice: "Birinchi ovoz",
    ach_first_voice_how: "Birinchi marta ovoz chiqarib o'qing",
    ach_moment_reflect: "Tafakkur lahzasi",
    ach_moment_reflect_how: "Kun hadisini o'qing",
    ach_ayah_by_ayah: "Oyat-baoyat",
    ach_ayah_by_ayah_how: "10 ta har xil oyat o'qing",
    ach_steady_tongue: "Tilda barqarorlik",
    ach_steady_tongue_how: "10 marta toza o'qing",
    ach_one_surah: "Bir sura, yaxshi bilingan",
    ach_one_surah_how: "Bir suraning barcha oyatlarini o'qing",
    ach_returning_daily: "Kundan kunga qaytish",
    ach_returning_daily_how: "Uch xil kuni mashq qiling",
    ach_words_to_carry: "Yodda qoladigan so'zlar",
    ach_words_to_carry_how: "Yetti kun hadis o'qing",
    ach_month_returning: "Qaytishlar oyi",
    ach_month_returning_how: "Oyning 20 kunida mashq qiling",
    ach_returning_heart: "Qaytgan qalb",
    ach_returning_heart_how: "Tanaffusdan so'ng qayting",
    ach_every_letter: "Har harf boshlanadigan joy",
    ach_every_letter_how: "Maxrajlar darsi",
    ach_beginning_hifz: "Hifz boshlanishi",
    ach_beginning_hifz_how: "Yodlashni boshlang",
    ach_first_ayahs: "Yodlangan ilk oyatlar",
    ach_first_ayahs_how: "Ilk oyatlarni yodlang",
    ach_surah_by_heart: "Yoddagi sura",
    ach_surah_by_heart_how: "Bir surani yod oling",
    ach_journey_completed: "Tugallangan yo'l",
    ach_journey_completed_how: "Bir yo'nalishni tugating",


    // ── Today: the five sections ──────────────────────────────────────
    today_kicker: "QAYERDA TOʻXTAGANDINGIZ",
    today_title: "Yoʻlingizni davom ettiring",
    since_recent: "Yaqinda oʻqilgan",
    since_hours: "{n} soat oldin oʻqilgan",
    since_days: "{n} kun oldin oʻqilgan",
    hero_surah: "{n}-SURA · {name}",
    hero_verse_of: "{n}-oyat, jami {of} tadan",
    hero_remaining: "taxminan {t} qoldi",
    // The app's own aside, not a quotation — nobody is credited because
    // nobody said it.
    today_aside: "Shoshilmaslik — ravonlik. Ravonlik — hurmat.",

    plan_kicker: "KUNINGIZ",
    plan_title: "Bugun uchun tinch reja",
    plan_count: "{n} ta qadam",
    plan_label_memorize: "YODLASH",
    plan_label_revise: "TAKRORLASH",
    plan_label_reflect: "TAFAKKUR",
    plan_type_recite: "oʻqish",
    plan_type_revise: "takrorlash",
    plan_reflect_title: "Kun oyati",
    plan_reflect_detail: "quyida · bir daqiqa",
    plan_minutes: "≈ {n} daq",
    plan_seconds: "≈ {n} son",

    hadith_kicker_section: "KUN HADISI",
    hadith_title: "Bugungi hadis",
    hadith_kicker: "PAYGʻAMBARIMIZ ﷺ AYTDILAR",
    hadith_meaning_note: "maʼno tarjimasi",
    hadith_draft_note:
      "Matn va manba raqami hali qori tomonidan tekshirilmagan.",
    reflect_kicker: "OʻQISH ODOBI HAQIDA",
    reflect_translation: "«Va Qurʼonni tartil bilan — shoshilmay, ravon oʻqing.»",
    reflect_source: "Muzzammil surasi · {sura}:{aya} · maʼno tarjimasi",

    learning_kicker: "OʻRGANISH",
    learning_title: "Boshlovchi darslar",

    stats_kicker: "HAFTANGIZ",
    stats_title: "Shu hafta",
    stats_week_label: "Hafta kunlari",
    stats_month_label: "Soʻnggi besh hafta",
    stats_trend_label: "Kunlik mashq vaqti",
    stats_verses: "OʻQILGAN OYAT",
    stats_time: "QURʼON BILAN",
    stats_accuracy: "TAJVID ANIQLIGI",
    stats_empty_title: "Bu hafta hali yozuv yoʻq",
    stats_empty_body:
      "Bir oyat oʻqing — shundan soʻng bu yerda haqiqiy raqamlar paydo boʻladi. Boʻsh joyni oʻylab topilgan sonlar bilan toʻldirmaymiz.",
    stats_empty_action: "Oyat tanlash",
    day_mon: "D",
    day_tue: "S",
    day_wed: "C",
    day_thu: "P",
    day_fri: "J",
    day_sat: "S",
    day_sun: "Y",

    // ── the account screen ────────────────────────────────────────────
    // TWO PROVIDERS NOW, so the tab pair is back - and this time with a
    // backend behind it. The strings deleted when the inert email form was
    // removed are rewritten rather than restored: the old set said "not ready
    // yet", which is exactly what is no longer true.
    auth_tagline: "Qurʼonni ovoz chiqarib oʻqing, tinch izoh oling.",
    auth_google: "Google bilan davom etish",
    auth_lang: "Til",
    auth_continue: "Hisobsiz davom etish",
    auth_anon_note:
      "{brand} hozir hisobsiz ishlaydi. Barcha imkoniyatlar shu qurilmada toʻliq ochiq.",
    // Shown ONLY when the server has no Google client configured, beneath the
    // disabled provider button. It no longer mentions email and password,
    // because there is no longer an email form to be pending - naming a method
    // the screen does not offer is how a stale disclaimer becomes a promise.
    auth_google_off:
      "Google orqali kirish hozir mavjud emas. Hisobsiz davom eting — hammasi shu qurilmada ishlaydi.",
    // Shown when this Google account already belongs to another Tilawah
    // account. Says what happened and what the learner can actually do -
    // nothing was lost and nothing was changed.
    auth_google_conflict:
      "Bu Google hisobi boshqa {brand} hisobiga ulangan. Hech narsa oʻzgarmadi. Shu hisobda qolish uchun hisobsiz davom eting.",
    auth_google_failed:
      "Google orqali kirib boʻlmadi. Qaytadan urinib koʻring yoki hisobsiz davom eting.",

    // ── email va parol ────────────────────────────────────────────────
    auth_tab_login: "Kirish",
    auth_tab_signup: "Roʻyxatdan oʻtish",
    auth_email: "Email",
    auth_password: "Parol",
    auth_email_ph: "siz@misol.com",
    // Said BEFORE they type, not after they are refused. A rule a learner
    // meets for the first time inside an error message is a rule they were
    // never given.
    auth_password_hint: "Kamida 10 ta belgi.",
    auth_show_password: "Parolni koʻrsatish",
    auth_hide_password: "Parolni yashirish",
    auth_do_login: "Kirish",
    auth_do_signup: "Hisob yaratish",
    auth_or: "yoki",
    auth_working: "Bajarilmoqda…",

    // Parolni tiklash.
    auth_forgot: "Parolni unutdingizmi?",
    auth_forgot_title: "Parolni tiklash",
    auth_forgot_body:
      "Email manzilingizni kiriting. Agar shu manzilda hisob boʻlsa, tiklash havolasini yuboramiz.",
    auth_forgot_send: "Havola yuborish",
    // DELIBERATELY SAYS "AGAR". The server answers the same thing for a
    // registered and an unregistered address, so this sentence must not
    // pretend it learned which one it was.
    auth_forgot_sent:
      "Agar shu manzilda hisob boʻlsa, tiklash havolasi yuborildi. Pochtangizni tekshiring.",
    auth_back: "Orqaga",

    auth_check_email:
      "Emailingizga tasdiqlash havolasi yuborildi. Havolani oching, soʻng kiring.",
    // Shown only when the server says nothing was actually sent - i.e. no mail
    // provider is wired yet. A developer must not be left wondering where the
    // message went, and a learner must not be told to check an empty inbox.
    auth_mail_off:
      "Eslatma: serverda pochta xizmati hali ulanmagan, shuning uchun xat yuborilmadi.",

    // ── xatolar. Hech qachon serverdan kelgan matn emas ────────────────
    // The server sends machine codes; these are the sentences. Nothing from
    // the API is ever printed to a learner as-is.
    auth_err_email: "Email manzil notoʻgʻri koʻrinadi.",
    auth_err_email_empty: "Email manzilingizni kiriting.",
    auth_err_password_empty: "Parolni kiriting.",
    auth_err_taken:
      "Bu email allaqachon roʻyxatdan oʻtgan. Kiring yoki parolni tiklang.",
    auth_err_has_email: "Bu hisobga allaqachon email ulangan.",
    // ONE SENTENCE FOR BOTH "wrong password" and "no such account", because
    // the server deliberately does not say which - and a client that guessed
    // would undo that.
    auth_err_credentials: "Email yoki parol notoʻgʻri.",
    auth_err_unverified:
      "Email hali tasdiqlanmagan. Pochtangizdagi havolani oching.",
    auth_err_throttled:
      "Juda koʻp urinish boʻldi. Bir necha daqiqadan soʻng qayta urinib koʻring.",
    auth_err_token:
      "Havola eskirgan yoki ishlatilgan. Yangi havola soʻrang.",
    auth_err_network:
      "Serverga ulanib boʻlmadi. Internetni tekshirib, qayta urinib koʻring.",
    auth_err_unknown: "Nimadir xato ketdi. Qaytadan urinib koʻring.",

    // Parol siyosati. Har bir kod - alohida gap.
    auth_pw_too_short: "Parol kamida 10 ta belgidan iborat boʻlsin.",
    auth_pw_too_long: "Parol juda uzun.",
    auth_pw_too_common: "Bu parol juda oddiy — boshqasini tanlang.",
    auth_pw_looks_like_email: "Parolda email manzilingiz boʻlmasin.",
    auth_pw_blank: "Parol faqat boʻsh joydan iborat boʻlmasin.",

    // ── pochtadagi havola ochilgan sahifalar ──────────────────────────
    mail_verify_title: "Emailni tasdiqlash",
    mail_verify_working: "Tekshirilmoqda…",
    mail_verify_ok: "Emailingiz tasdiqlandi. Endi kirishingiz mumkin.",
    mail_reset_title: "Yangi parol",
    mail_reset_body:
      "Yangi parolni kiriting. Xavfsizlik uchun barcha qurilmalarda qaytadan kirishingiz kerak boʻladi.",
    mail_reset_do: "Parolni saqlash",
    mail_reset_ok: "Parol yangilandi. Endi yangi parol bilan kiring.",
    mail_open_app: "Ilovaga oʻtish",

    // ── onboarding. No sign up, no log in: there are no accounts, and the
    // consent step is the real decision being made here.
    onboard_welcome: "{brand}ga xush kelibsiz",
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

    // ── the knowledge assessment. Asked ONCE, in onboarding. The result is a
    // setting in Profile, never a badge or a banner in the app.
    assess_title: "Tajvid bilimingiz qay darajada?",
    assess_body:
      "Uchta qisqa savol. Bu imtihon emas — javoblaringiz faqat boshlangʻich sozlamani belgilaydi va keyin Profilda oʻzgartiriladi.",
    assess_q_alphabet: "Arab alifbosini bilasizmi?",
    assess_a_alphabet_0: "Yoʻq, hali oʻrganmaganman",
    assess_a_alphabet_1: "Koʻp harflarni tanijman",
    assess_a_alphabet_2: "Ha, erkin oʻqiyman",
    assess_q_tajweed: "Tajvid qoidalarini oʻrganganmisiz?",
    assess_a_tajweed_0: "Yoʻq, hech qachon",
    assess_a_tajweed_1: "Biroz — asosiy qoidalarni",
    assess_a_tajweed_2: "Ha, ustoz bilan oʻqiganman",
    assess_q_fluency: "Oʻqishingizni qanday baholaysiz?",
    assess_a_fluency_0: "Hali boshlamaganman",
    assess_a_fluency_1: "Sekin, xatolar bilan",
    assess_a_fluency_2: "Ravon oʻqiyman",
    level_beginner: "Boshlangʻich",
    level_intermediate: "Oʻrta",
    level_advanced: "Yuqori",
    level_setting: "Bilim darajasi",
    level_setting_note:
      "Onboardingda soʻralgan. Istalgan vaqtda oʻzgartirasiz.",

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
    profile_group_account: "Hisob",
    profile_group_prefs: "Sozlamalar",
    profile_group_privacy: "Maxfiylik",
    profile_group_about: "Ilova haqida",
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
    // The opening. A learner arriving at results is told what is about to
    // happen, not how many faults were counted against them. verdict_title is
    // kept because the history screen still replays old attempts with it.
    verdict_title: "Koʻrib chiqadigan {n} ta joy bor",
    verdict_one_at_a_time: "Bu safar bitta narsani tuzatamiz",
    verdict_one_place: "Keling, shu joyni tuzataylik",
    verdict_body:
      "Nima boʻlgani va qanday tuzatish kerakligi quyida yozilgan. Shoshilmang.",
    verdict_all_fixed: "Hammasi tuzatildi",
    verdict_all_fixed_body: "Endi oyatni boshidan bir marta oʻqib koʻring.",
    // Said ONLY when the score actually supports it — see Feedback.tsx. Praise
    // that is not earned is praise the learner learns to discount, and once
    // discounted it never works again.
    verdict_all_fixed_earned:
      "Qolgan qismi toʻgʻri chiqdi — faqat shu joyga eʼtibor berdik. Endi oyatni boshidan oʻqing.",
    // What is still waiting, as a count and nothing more.
    more_remaining: "Hali {n} ta joy bor — buni tugatgach koʻrsatamiz",
    // Opens every card. Not a diagnosis, an invitation.
    card_framing: "Keling, shu joyni tuzataylik",
    // The two disclosures on a restructured card. UI copy, not tajweed — the
    // sentences they reveal are authored and gated; these labels are not.
    card_rule_toggle: "Qoida",
    card_explain_simply: "Oddiy qilib tushuntiring",
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

    // ── the practice ladder. The FIRST rung differs by error type — see
    // engine/practice.py. Only an articulation error opens on the bare letter;
    // an omission, an insertion and a duration error each open on the word,
    // said slowly, with the thing to attend to named here. Each label is an
    // instruction, because on those three rungs the same word is shown twice
    // and only the label says what is different about the first pass.
    rung_letter: "Faqat shu harf",
    rung_syllables: "Harakatlar bilan",
    rung_word_include: "Sekin ayting — tushib qolgan harfni eshitilsin",
    rung_word_omit: "Sekin ayting — ortiqcha tovushsiz",
    rung_word_hold: "Sekin ayting — cho‘zilishni sanab ushlang",
    rung_word: "Shu soʻz",
    // Same rung, named differently when a SLOW pass at the same word came
    // before it — otherwise two rungs show the identical word under the
    // identical label and read as a duplicate rather than as a second pass.
    rung_word_normal: "Endi oddiy tezlikda",
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
    // Closed by the attempt cap, not by getting it right. Says so plainly
    // rather than borrowing the praise line - see the Fixed component.
    fixed_enough: "Bu yetarli, davom etamiz.",
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

    // ── the restructured navigation ──────────────────────────────────────
    nav_home: "Bosh sahifa",
    nav_tutor: "Ustoz",
    nav_progress: "Natijalar",
    nav_settings: "Sozlamalar",

    // ── the greeting. Time of day, in the learner's language, and the
    //    prayer-adjacent hours are named the way people name them here:
    //    "tong" is the hour around Bomdod, not merely "early". ─────────────
    greet_dawn: "Tong muborak",
    greet_morning: "Xayrli tong",
    greet_afternoon: "Xayrli kun",
    greet_evening: "Xayrli kech",
    greet_night: "Xayrli tun",

    // ── the continue card ────────────────────────────────────────────────
    home_continue_kicker: "DAVOM ETTIRING",
    home_continue_cta: "Oʻqishni davom ettirish",
    home_begin_cta: "Birinchi oyatni tanlash",

    // ── the four figures ─────────────────────────────────────────────────
    stat_streak: "Ketma-ket kun",
    stat_hasanat: "Hasanat",
    stat_ayat: "Oʻqilgan oyat",
    stat_time: "Mashq vaqti",
    stat_none_yet: "Hali boshlanmagan",
    stats_kicker_home: "HISOB",
    stats_title_home: "Sizning hisobingiz",
    stats_empty_note:
      "Birinchi oyatni oʻqiganingizdan soʻng bu raqamlar toʻlib boradi. Hozircha hech narsa oʻylab topilmagan.",

    // ── hasanat. The claim and its source travel together; see the card. ──
    hasanat_kicker: "HASANAT",
    hasanat_claim:
      "«Kim Allohning Kitobidan bir harf oʻqisa, unga bir yaxshilik bor; har bir yaxshilik esa oʻn baravar qilib beriladi.»",
    // Said plainly, and not in small print: a counter cannot know what is
    // accepted. It knows how many letters were read.
    hasanat_caveat:
      "Bu — oʻqilgan harflar hisobi, ajr haqidagi daʼvo emas. Ajr Alloh huzurida.",

    // ── rank ─────────────────────────────────────────────────────────────
    rank_kicker: "DARAJA",
    rank_mubtadi: "Mubtadi",
    rank_tolib: "Tolib",
    rank_qori: "Qori",
    rank_mutqin: "Mutqin",
    rank_mujavvid: "Mujavvid",
    rank_mubtadi_note: "Yoʻlning boshi. Kuniga bir oyat ham yetarli.",
    rank_tolib_note: "Muntazam oʻqiyapsiz — odat shakllanmoqda.",
    rank_qori_note: "Oyatlarni ravon oʻqiyapsiz.",
    rank_mutqin_note: "Harflar joyida, oʻqish aniq.",
    rank_mujavvid_note: "Tajvid bilan, goʻzal oʻqish.",
    rank_to_next: "{name} darajasigacha {n} XP",
    rank_top: "Eng yuqori daraja",
    rank_xp: "{n} XP",

    // ── the week strip ───────────────────────────────────────────────────
    week_kicker: "SHU HAFTA",
    week_title: "Haftangiz",
    day_state_done: "oʻqilgan",
    day_state_missed: "oʻqilmagan",
    day_state_pending: "hali oldinda",

    // ── suggested next ───────────────────────────────────────────────────
    journey_next_kicker: "YOʻLINGIZ",
    journey_next_title: "Keyingi suralar",
    journey_ayat_n: "{n} oyat",

    // ── the tutor card ───────────────────────────────────────────────────
    // No persona, no name, no face. It describes what the tutor DOES, which
    // is built, rather than who it is, which is nobody.
    tutor_kicker: "AI USTOZ",
    tutor_title: "Oʻqing — ustoz tinglaydi",
    tutor_body:
      "Oyatni ovoz chiqarib oʻqing. Qaysi harfda, qaysi soʻzda xato boʻlganini aniq koʻrsatadi va uni qanday tuzatishni tushuntiradi.",
    tutor_cta: "Hozir oʻqish",
    tutor_no_face:
      "Bu — dastur, inson emas. Shuning uchun bu yerda hech kimning surati yoʻq.",

    // ── the sura picker ──────────────────────────────────────────────────
    sura_count_n: "{n} ta sura",
    filter_all: "Barchasi",
    filter_makki: "Makkiy",
    filter_madani: "Madaniy",
    filter_started: "Boshlangan",
    place_makki: "Makkiy",
    place_madani: "Madaniy",

    // ── study mode, per sura ─────────────────────────────────────────────
    study_mode: "Ish turi",
    study_read: "Oʻqish",
    study_memorize: "Yodlash",
    coming_soon: "Tez orada",

    // ── moving between ayat ──────────────────────────────────────────────
    // prev_ayah / next_ayah are NOT redefined here: the verse-by-verse reader
    // already has them, with the same words. The practice arrows point at the
    // same idea and reuse the same strings.
    exit_practice: "Boshqa sura tanlash",

    // ── appearance ───────────────────────────────────────────────────────
    theme_label: "Koʻrinish",
    theme_dark: "Tungi",
    theme_light: "Kunduzgi",
    theme_help:
      "Tungi koʻrinish — chuqur zangori fon, tilla yoritish. Kunduzgi — fil suyagi qogʻoz va guruch ranglari.",
    settings_section: "SOZLAMALAR",
    lang_label: "Til",

    // ── the long-ayah fallback ───────────────────────────────────────────
    // Blames the length, explains what the app did, asks nothing. The learner
    // never chose this and never chooses a chunk — but they are told when the
    // range on screen is not the whole ayah, because scoring part of an ayah
    // as though it were all of it is the one thing worse than the old picker.
    long_ayah_note:
      "Bu oyat uzun — hozircha uning boshlangʻich qismi ustida ishlaymiz.",
    long_wait_note: "Bu oyat uzun, biroz vaqt oladi.",

    // ── the comparison, after the result ─────────────────────────────────
    compare_mine: "Mening oʻqishim",
    compare_reciter: "Qori oʻqishi",

    // ── rule badges: what this ayah CONTAINS ─────────────────────────────
    rules_title: "Shu oyatdagi qoidalar",
    rules_target: "Cho'zilishi",
    rules_uz_only:
      "Bu qoidalar hozircha faqat o'zbek tilida — ruscha tarjimasi tayyorlanmoqda.",

    // ── which ayah you are on ────────────────────────────────────────────
    ayah: "Oyat",

    // ── notifications ────────────────────────────────────────────────────
    notif_open: "Bildirishnomalar",
    notif_title: "Bildirishnomalar",
    notif_close: "Yopish",
    notif_mark_all: "Hammasini oʻqilgan deb belgilash",
    notif_empty_title: "Hozircha bildirishnoma yoʻq",
    notif_empty_body: "Maqsad qoʻysangiz, eslatmalar shu yerda koʻrinadi.",
    // Said plainly, because a bell that never rings on the lock screen is a
    // promise the app has not kept yet. See lib/notifications.ts.
    notif_delivery_note:
      "Eslatmalar hozircha faqat shu yerda koʻrinadi. Telefon bildirishnomalari keyinroq ulanadi.",
    notif_now: "hozir",
    notif_min: "{n} daqiqa oldin",
    notif_hour: "{n} soat oldin",
    notif_day: "{n} kun oldin",

    // ── goals ────────────────────────────────────────────────────────────
    goal_home_kicker: "MAQSAD",
    goal_home_title: "Oʻzingizga maqsad qoʻying",
    goal_home_body: "Kichik, har kuni bajariladigan maqsad — eng yaxshi boshlanish.",
    goal_new_cta: "Yangi maqsad",
    goal_screen_sub: "Bittasini tanlang. Keyin istalgan vaqtda oʻzgartirasiz.",
    goal_p_ayah_title: "Har kuni bitta oyat",
    goal_p_ayah_body: "Kuniga bir oyat oʻqiysiz.",
    goal_p_minutes_title: "Har kuni 5 daqiqa mashq",
    goal_p_minutes_body: "Kuniga besh daqiqa ovoz chiqarib oʻqiysiz.",
    goal_p_sura_title: "Haftasiga bitta sura",
    goal_p_sura_body: "Haftada bir surani toʻliq oʻqiysiz.",
    goal_p_custom_title: "Oʻzim tanlayman",
    goal_p_custom_body: "Miqdorini va qachonligini oʻzingiz belgilaysiz.",
    goal_what: "Nimani?",
    goal_how_much: "Qancha?",
    goal_how_often: "Qachon?",
    goal_unit_ayah: "oyat",
    goal_unit_minute: "daqiqa",
    goal_unit_sura: "sura",
    goal_every_day: "Har kuni",
    goal_every_week: "Har hafta",
    goal_more: "Koʻproq",
    goal_less: "Kamroq",
    goal_remind: "Eslatma yubor",
    goal_remind_help: "Belgilangan vaqtda eslatib turamiz.",
    goal_remind_time: "Vaqti",
    goal_save: "Maqsadni saqlash",
    goal_cancel: "Bekor qilish",
    goal_active_kicker: "SIZNING MAQSADINGIZ",
    goal_change: "Oʻzgartirish",
    goal_remove: "Maqsadni oʻchirish",
    goal_reminder_at: "Eslatma: {t}",
    goal_no_reminder: "Eslatmasiz",
    goal_sum_day: "Har kuni {n} {unit}",
    goal_sum_week: "Har hafta {n} {unit}",
    goal_notif_title: "Mashq vaqti",
    goal_notif_body: "{goal}. Hozir boshlaymizmi?",

    // weakness tracking
    weak_title: "Zaif tomonlar",
    weak_count: "{n} marta",
    weak_recent: "Soʻnggi 7 kun: {n}",
    weak_older: "Oldingi: {n}",
    weak_corrected: "{n} tasi tuzatildi",
    weak_rate: "Tuzatish: {n}%",
    weak_l1_label: "Til taʼsiri",
    weak_empty_title: "Hali xatolar yoʻq",
    weak_empty_body: "Oʻqishni boshlang — xatolar tahlili shu yerda paydo boʻladi",
    weak_show_all: "Hammasini koʻrsatish",
    weak_improving: "Yaxshilanmoqda",
    weak_worsening: "Koʻpaymoqda",
    weak_stable: "Barqaror",
    weak_trend: "Tendensiya",
    weak_first: "Boshida {n}%",
    weak_latest: "Hozir {n}%",
    weak_not_enough: "Maʼlumot yetarli emas",
    weak_before: "Oldin",
    weak_after: "Hozir",
    weak_fixed: "Tuzatildi",
    weak_lesson: "Mashq qilish",
    weak_listen: "Tinglash",
    weak_ask_teacher: "Ustoz bilan tekshiring",
    weak_makhraj: "Makhraj",
    focus_kicker: "BUGUNGI DIQQAT",
    focus_title: "Eng koʻp xato",
    focus_cta: "Mashq qilish",
    focus_recent_n: "Soʻnggi 7 kunda {n} marta",
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
    nav_bookmark: "Сохранённое место",
    welcome_1_title: "Ваш путь к Корану — с проводником",
    welcome_1_body:
      "{brand} подскажет, с чего начать и что делать дальше. Составлять план самому не нужно.",
    welcome_2_title: "Читайте — мы слушаем",
    welcome_2_body:
      "Прочитайте аят вслух. {brand} покажет, в какой букве и в каком слове была ошибка, и объяснит, как её исправить.",
    welcome_3_title: "Понемногу каждый день",
    welcome_3_body:
      "Несколько минут в день. Ни оценок, ни рейтингов, ни соревнования — только вы и текст.",
    welcome_start: "Начнём",
    onboard_choose_later: "Выберу позже",
    personalize_done: "Готово",

    q_goal: "Что привело вас в {brand}?",
    q_stage: "Где вы на своём пути к Корану?",
    q_focus: "С чего начнём?",
    q_minutes: "Сколько времени в день вы можете уделить?",
    q_when: "Когда вам удобно заниматься?",

    goal_recitation: "Улучшить чтение",
    goal_tajweed: "Изучить таджвид",
    goal_memorize: "Учить Коран наизусть",
    goal_habit: "Выработать ежедневную привычку",
    goal_understand: "Больше понимать Коран",
    goal_everything: "Всего понемногу",

    stage_beginning: "Только начинаю",
    stage_improving: "Читаю, но хочу лучше",
    stage_comfortable: "Читаю уверенно",
    stage_memorizing: "Сейчас учу наизусть",

    focus_recitation: "Чтение",
    focus_tajweed: "Таджвид",
    focus_memorization: "Заучивание",
    focus_consistency: "Постоянство",
    focus_understanding: "Понимание",

    min_5: "5 минут",
    min_10: "10 минут",
    min_15: "15 минут",
    min_20: "20 минут",
    min_30: "30+ минут",

    when_after_fajr: "После фаджра",
    when_morning: "Утром",
    when_afternoon: "Днём",
    when_after_maghrib: "После магриба",
    when_evening: "Вечером",
    when_later: "Выберу сам",

    journey_mine: "МОЙ ПУТЬ",
    journey_goal: "Цель",
    journey_daily: "Время в день",
    journey_focus: "Направление",
    journey_when: "Время занятий",
    journey_stage: "Уровень",
    journey_weekly: "Намерение на неделю",
    journey_build_title: "Давайте построим ваш путь.",
    journey_build_body: "На основе ваших ответов. Изменить можно в любой момент.",
    journey_create_cta: "Создать мой путь",
    journey_change: "Изменить ответы",
    journey_ready_title: "Ваш путь готов.",
    journey_today: "СЕГОДНЯ",
    journey_this_week: "НА ЭТОЙ НЕДЕЛЕ",
    journey_path: "ТЕКУЩЕЕ НАПРАВЛЕНИЕ",
    journey_begin_cta: "Начать сегодняшний путь",
    minutes_n: "{n} минут",
    minutes_per_day: "{n} минут в день",
    sessions_n: "{n} раз",
    path_unset: "Пока не выбрано",
    step_practice: "Практика",
    step_practice_note: "Прочитайте аят и получите разбор",
    step_reflect: "Размышление",
    step_reflect_note: "Хадис дня",

    ach_recent: "НЕДАВНИЕ ДОСТИЖЕНИЯ",
    ach_view_all: "Все →",
    ach_all: "ДОСТИЖЕНИЯ",
    ach_count: "{n} из {of}",
    ach_not_built:
      "Этот раздел ещё не готов — пока это достижение получить нельзя.",
    ach_first_step: "Первый шаг",
    ach_first_step_how: "Создайте свой путь",
    ach_first_voice: "Первый голос",
    ach_first_voice_how: "Прочитайте вслух в первый раз",
    ach_moment_reflect: "Момент размышления",
    ach_moment_reflect_how: "Прочитайте хадис дня",
    ach_ayah_by_ayah: "Аят за аятом",
    ach_ayah_by_ayah_how: "Прочитайте 10 разных аятов",
    ach_steady_tongue: "Уверенность в чтении",
    ach_steady_tongue_how: "10 чистых чтений",
    ach_one_surah: "Одна сура, хорошо знакомая",
    ach_one_surah_how: "Прочитайте все аяты одной суры",
    ach_returning_daily: "День за днём",
    ach_returning_daily_how: "Занимайтесь в три разных дня",
    ach_words_to_carry: "Слова, которые остаются",
    ach_words_to_carry_how: "Семь дней с хадисом",
    ach_month_returning: "Месяц возвращений",
    ach_month_returning_how: "Занимайтесь 20 дней за месяц",
    ach_returning_heart: "Возвращающееся сердце",
    ach_returning_heart_how: "Вернитесь после перерыва",
    ach_every_letter: "Где начинается каждая буква",
    ach_every_letter_how: "Урок махраджей",
    ach_beginning_hifz: "Начало хифза",
    ach_beginning_hifz_how: "Начните заучивание",
    ach_first_ayahs: "Первые выученные аяты",
    ach_first_ayahs_how: "Выучите первые аяты",
    ach_surah_by_heart: "Сура наизусть",
    ach_surah_by_heart_how: "Выучите суру целиком",
    ach_journey_completed: "Завершённый путь",
    ach_journey_completed_how: "Завершите направление",


    today_kicker: "ГДЕ ВЫ ОСТАНОВИЛИСЬ",
    today_title: "Продолжите свой путь",
    since_recent: "Читали недавно",
    since_hours: "Читали {n} ч назад",
    since_days: "Читали {n} дн назад",
    hero_surah: "СУРА {n} · {name}",
    hero_verse_of: "Аят {n} из {of}",
    hero_remaining: "осталось около {t}",
    today_aside: "Медленно — значит ровно. Ровно — значит бережно.",

    plan_kicker: "ВАШ ДЕНЬ",
    plan_title: "Спокойный план на сегодня",
    plan_count: "{n} шага",
    plan_label_memorize: "ЗАУЧИТЬ",
    plan_label_revise: "ПОВТОРИТЬ",
    plan_label_reflect: "РАЗМЫШЛЕНИЕ",
    plan_type_recite: "чтение",
    plan_type_revise: "повторение",
    plan_reflect_title: "Аят дня",
    plan_reflect_detail: "ниже · одна минута",
    plan_minutes: "≈ {n} мин",
    plan_seconds: "≈ {n} сек",

    hadith_kicker_section: "ХАДИС ДНЯ",
    hadith_title: "Хадис на сегодня",
    hadith_kicker: "ПРОРОК ﷺ СКАЗАЛ",
    hadith_meaning_note: "перевод смысла",
    hadith_draft_note:
      "Текст и номер источника ещё не проверены кори.",
    reflect_kicker: "ОБ ЭТИКЕТЕ ЧТЕНИЯ",
    reflect_translation: "«И читай Коран размеренно — не торопясь, ровно.»",
    reflect_source: "Сура Аль-Муззаммиль · {sura}:{aya} · перевод смысла",

    learning_kicker: "ОБУЧЕНИЕ",
    learning_title: "Вводные уроки",

    stats_kicker: "ВАША НЕДЕЛЯ",
    stats_title: "На этой неделе",
    stats_week_label: "Дни недели",
    stats_month_label: "Последние пять недель",
    stats_trend_label: "Время практики по дням",
    stats_verses: "ПРОЧИТАНО АЯТОВ",
    stats_time: "С КОРАНОМ",
    stats_accuracy: "ТОЧНОСТЬ ТАДЖВИДА",
    stats_empty_title: "На этой неделе записей пока нет",
    stats_empty_body:
      "Прочитайте один аят — и здесь появятся настоящие цифры. Мы не заполняем это место выдуманными числами.",
    stats_empty_action: "Выбрать аят",
    day_mon: "П",
    day_tue: "В",
    day_wed: "С",
    day_thu: "Ч",
    day_fri: "П",
    day_sat: "С",
    day_sun: "В",

    auth_tagline: "Читайте Коран вслух и получайте спокойный разбор.",
    auth_google: "Продолжить с Google",
    auth_lang: "Язык",
    auth_continue: "Продолжить без аккаунта",
    auth_anon_note:
      "Сейчас {brand} работает без аккаунта. Все возможности полностью доступны на этом устройстве.",
    auth_google_off:
      "Вход через Google сейчас недоступен. Продолжите без аккаунта — всё работает на этом устройстве.",
    auth_google_conflict:
      "Этот аккаунт Google уже привязан к другому аккаунту {brand}. Ничего не изменилось. Чтобы остаться в текущем, продолжите без аккаунта.",
    auth_google_failed:
      "Не удалось войти через Google. Попробуйте ещё раз или продолжите без аккаунта.",

    auth_tab_login: "Вход",
    auth_tab_signup: "Регистрация",
    auth_email: "Email",
    auth_password: "Пароль",
    auth_email_ph: "вы@пример.com",
    auth_password_hint: "Не менее 10 символов.",
    auth_show_password: "Показать пароль",
    auth_hide_password: "Скрыть пароль",
    auth_do_login: "Войти",
    auth_do_signup: "Создать аккаунт",
    auth_or: "или",
    auth_working: "Выполняется…",

    auth_forgot: "Забыли пароль?",
    auth_forgot_title: "Сброс пароля",
    auth_forgot_body:
      "Введите email. Если на этот адрес есть аккаунт, мы отправим ссылку для сброса.",
    auth_forgot_send: "Отправить ссылку",
    auth_forgot_sent:
      "Если на этот адрес есть аккаунт, ссылка для сброса отправлена. Проверьте почту.",
    auth_back: "Назад",

    auth_check_email:
      "На ваш email отправлена ссылка для подтверждения. Откройте её, затем войдите.",
    auth_mail_off:
      "Примечание: почтовый сервис на сервере ещё не подключён, поэтому письмо не отправлено.",

    auth_err_email: "Email выглядит неверно.",
    auth_err_email_empty: "Введите ваш email.",
    auth_err_password_empty: "Введите пароль.",
    auth_err_taken:
      "Этот email уже зарегистрирован. Войдите или сбросьте пароль.",
    auth_err_has_email: "К этому аккаунту уже привязан email.",
    auth_err_credentials: "Неверный email или пароль.",
    auth_err_unverified:
      "Email ещё не подтверждён. Откройте ссылку из письма.",
    auth_err_throttled:
      "Слишком много попыток. Попробуйте через несколько минут.",
    auth_err_token:
      "Ссылка устарела или уже использована. Запросите новую.",
    auth_err_network:
      "Не удалось связаться с сервером. Проверьте интернет и попробуйте снова.",
    auth_err_unknown: "Что-то пошло не так. Попробуйте ещё раз.",

    auth_pw_too_short: "Пароль должен быть не короче 10 символов.",
    auth_pw_too_long: "Пароль слишком длинный.",
    auth_pw_too_common: "Этот пароль слишком простой — выберите другой.",
    auth_pw_looks_like_email: "Пароль не должен содержать ваш email.",
    auth_pw_blank: "Пароль не может состоять из одних пробелов.",

    mail_verify_title: "Подтверждение email",
    mail_verify_working: "Проверяем…",
    mail_verify_ok: "Ваш email подтверждён. Теперь можно войти.",
    mail_reset_title: "Новый пароль",
    mail_reset_body:
      "Введите новый пароль. В целях безопасности потребуется войти заново на всех устройствах.",
    mail_reset_do: "Сохранить пароль",
    mail_reset_ok: "Пароль обновлён. Теперь войдите с новым паролем.",
    mail_open_app: "Перейти в приложение",

    onboard_welcome: "Добро пожаловать в {brand}",
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

    assess_title: "Каков ваш уровень таджвида?",
    assess_body:
      "Три коротких вопроса. Это не экзамен — ответы задают лишь начальную настройку, и её можно изменить в Профиле.",
    assess_q_alphabet: "Знаете ли вы арабский алфавит?",
    assess_a_alphabet_0: "Нет, пока не изучал",
    assess_a_alphabet_1: "Узнаю большинство букв",
    assess_a_alphabet_2: "Да, читаю свободно",
    assess_q_tajweed: "Изучали ли вы правила таджвида?",
    assess_a_tajweed_0: "Нет, никогда",
    assess_a_tajweed_1: "Немного — основные правила",
    assess_a_tajweed_2: "Да, занимался с устазом",
    assess_q_fluency: "Как вы оцениваете своё чтение?",
    assess_a_fluency_0: "Ещё не начинал",
    assess_a_fluency_1: "Медленно, с ошибками",
    assess_a_fluency_2: "Читаю бегло",
    level_beginner: "Начальный",
    level_intermediate: "Средний",
    level_advanced: "Высокий",
    level_setting: "Уровень знаний",
    level_setting_note:
      "Спрошено при первом запуске. Можно изменить в любой момент.",

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
    profile_group_account: "Аккаунт",
    profile_group_prefs: "Настройки",
    profile_group_privacy: "Конфиденциальность",
    profile_group_about: "О приложении",
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
    verdict_one_at_a_time: "В этот раз исправим одно",
    verdict_one_place: "Давайте поправим это место",
    verdict_body:
      "Ниже написано, что произошло и как это исправить. Не торопитесь.",
    verdict_all_fixed: "Всё исправлено",
    verdict_all_fixed_body: "Теперь прочитайте аят целиком ещё раз.",
    verdict_all_fixed_earned:
      "Остальное прочитано верно — мы занимались только этим местом. Теперь прочитайте аят с начала.",
    more_remaining: "Осталось ещё {n} — покажем, когда закончите это",
    card_framing: "Давайте поправим это место",
    card_rule_toggle: "Правило",
    card_explain_simply: "Объяснить проще",
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
    rung_word_include: "Медленно — так, чтобы пропущенная буква прозвучала",
    rung_word_omit: "Медленно — без лишнего звука",
    rung_word_hold: "Медленно — считая долготу",
    rung_word: "Это слово",
    rung_word_normal: "Теперь в обычном темпе",
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
    fixed_enough: "Этого достаточно, идём дальше.",
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

    nav_home: "Главная",
    nav_tutor: "Наставник",
    nav_progress: "Прогресс",
    nav_settings: "Настройки",

    greet_dawn: "Благословенного рассвета",
    greet_morning: "Доброе утро",
    greet_afternoon: "Добрый день",
    greet_evening: "Добрый вечер",
    greet_night: "Доброй ночи",

    home_continue_kicker: "ПРОДОЛЖИТЬ",
    home_continue_cta: "Продолжить чтение",
    home_begin_cta: "Выбрать первый аят",

    stat_streak: "Дней подряд",
    stat_hasanat: "Хасанат",
    stat_ayat: "Прочитано аятов",
    stat_time: "Время практики",
    stat_none_yet: "Ещё не начато",
    stats_kicker_home: "СЧЁТ",
    stats_title_home: "Ваш счёт",
    stats_empty_note:
      "Эти числа начнут расти после первого прочитанного аята. Пока здесь ничего не придумано.",

    hasanat_kicker: "ХАСАНАТ",
    hasanat_claim:
      "«Кто прочитает одну букву из Книги Аллаха, тому — одно доброе дело, а доброе дело воздаётся десятикратно.»",
    hasanat_caveat:
      "Это подсчёт прочитанных букв, а не утверждение о награде. Награда — у Аллаха.",

    rank_kicker: "СТУПЕНЬ",
    rank_mubtadi: "Мубтади",
    rank_tolib: "Толиб",
    rank_qori: "Кори",
    rank_mutqin: "Муткин",
    rank_mujavvid: "Муджаввид",
    rank_mubtadi_note: "Начало пути. Достаточно одного аята в день.",
    rank_tolib_note: "Вы читаете регулярно — привычка складывается.",
    rank_qori_note: "Аяты читаются уверенно.",
    rank_mutqin_note: "Буквы на месте, чтение точное.",
    rank_mujavvid_note: "С таджвидом, красивое чтение.",
    rank_to_next: "До ступени «{name}» — {n} XP",
    rank_top: "Высшая ступень",
    rank_xp: "{n} XP",

    week_kicker: "НА ЭТОЙ НЕДЕЛЕ",
    week_title: "Ваша неделя",
    day_state_done: "прочитано",
    day_state_missed: "не прочитано",
    day_state_pending: "ещё впереди",

    journey_next_kicker: "ВАШ ПУТЬ",
    journey_next_title: "Следующие суры",
    journey_ayat_n: "{n} аятов",

    tutor_kicker: "ИИ-НАСТАВНИК",
    tutor_title: "Читайте — наставник слушает",
    tutor_body:
      "Прочитайте аят вслух. Наставник покажет, в какой букве и в каком слове была ошибка, и объяснит, как её исправить.",
    tutor_cta: "Читать сейчас",
    tutor_no_face:
      "Это программа, а не человек. Поэтому здесь нет ничьего изображения.",

    sura_count_n: "Сур: {n}",
    filter_all: "Все",
    filter_makki: "Мекканские",
    filter_madani: "Мединские",
    filter_started: "Начатые",
    place_makki: "Мекканская",
    place_madani: "Мединская",

    study_mode: "Режим работы",
    study_read: "Чтение",
    study_memorize: "Заучивание",
    coming_soon: "Скоро",

    exit_practice: "Выбрать другую суру",

    theme_label: "Оформление",
    theme_dark: "Ночное",
    theme_light: "Дневное",
    theme_help:
      "Ночное — глубокий синий фон и золотое свечение. Дневное — цвет слоновой кости и латунь.",
    settings_section: "НАСТРОЙКИ",
    lang_label: "Язык",

    long_ayah_note:
      "Этот аят длинный — пока работаем над его начальной частью.",
    long_wait_note: "Этот аят длинный, потребуется немного времени.",

    compare_mine: "Моё чтение",
    compare_reciter: "Чтение чтеца",

    // ── rule badges: what this ayah CONTAINS ─────────────────────────────
    rules_title: "Правила в этом аяте",
    rules_target: "Протяжение",
    rules_uz_only:
      "Эти правила пока только на узбекском — русский перевод готовится.",

    // ── which ayah you are on ────────────────────────────────────────────
    ayah: "Аят",

    // ── notifications ────────────────────────────────────────────────────
    notif_open: "Уведомления",
    notif_title: "Уведомления",
    notif_close: "Закрыть",
    notif_mark_all: "Отметить все как прочитанные",
    notif_empty_title: "Пока уведомлений нет",
    notif_empty_body: "Поставьте цель — и напоминания появятся здесь.",
    notif_delivery_note:
      "Пока напоминания видны только здесь. Системные уведомления телефона подключим позже.",
    notif_now: "только что",
    notif_min: "{n} мин назад",
    notif_hour: "{n} ч назад",
    notif_day: "{n} дн назад",

    // ── goals ────────────────────────────────────────────────────────────
    goal_home_kicker: "ЦЕЛЬ",
    goal_home_title: "Поставьте себе цель",
    goal_home_body: "Небольшая ежедневная цель — самое лучшее начало.",
    goal_new_cta: "Новая цель",
    goal_screen_sub: "Выберите одну. Потом сможете изменить в любой момент.",
    goal_p_ayah_title: "Один аят каждый день",
    goal_p_ayah_body: "Читаете по одному аяту в день.",
    goal_p_minutes_title: "5 минут практики каждый день",
    goal_p_minutes_body: "Пять минут чтения вслух в день.",
    goal_p_sura_title: "Одна сура в неделю",
    goal_p_sura_body: "За неделю прочитываете одну суру.",
    goal_p_custom_title: "Выберу сам",
    goal_p_custom_body: "Сами укажете сколько и как часто.",
    goal_what: "Что?",
    goal_how_much: "Сколько?",
    goal_how_often: "Как часто?",
    goal_unit_ayah: "аятов",
    goal_unit_minute: "минут",
    goal_unit_sura: "сур",
    goal_every_day: "Каждый день",
    goal_every_week: "Каждую неделю",
    goal_more: "Больше",
    goal_less: "Меньше",
    goal_remind: "Присылать напоминание",
    goal_remind_help: "Напомним в указанное время.",
    goal_remind_time: "Время",
    goal_save: "Сохранить цель",
    goal_cancel: "Отмена",
    goal_active_kicker: "ВАША ЦЕЛЬ",
    goal_change: "Изменить",
    goal_remove: "Удалить цель",
    goal_reminder_at: "Напоминание: {t}",
    goal_no_reminder: "Без напоминания",
    goal_sum_day: "Каждый день {n} {unit}",
    goal_sum_week: "Каждую неделю {n} {unit}",
    goal_notif_title: "Время практики",
    goal_notif_body: "{goal}. Начнём?",

    // weakness tracking
    weak_title: "Слабые стороны",
    weak_count: "{n} раз",
    weak_recent: "Последние 7 дней: {n}",
    weak_older: "Ранее: {n}",
    weak_corrected: "{n} исправлено",
    weak_rate: "Исправление: {n}%",
    weak_l1_label: "Влияние языка",
    weak_empty_title: "Ошибок пока нет",
    weak_empty_body: "Начните читать — анализ ошибок появится здесь",
    weak_show_all: "Показать все",
    weak_improving: "Улучшается",
    weak_worsening: "Ухудшается",
    weak_stable: "Стабильно",
    weak_trend: "Тенденция",
    weak_first: "Сначала {n}%",
    weak_latest: "Сейчас {n}%",
    weak_not_enough: "Недостаточно данных",
    weak_before: "До",
    weak_after: "После",
    weak_fixed: "Исправлено",
    weak_lesson: "Практиковать",
    weak_listen: "Слушать",
    weak_ask_teacher: "Проконсультируйтесь с устазом",
    weak_makhraj: "Махрадж",
    focus_kicker: "ФОКУС ДНЯ",
    focus_title: "Частая ошибка",
    focus_cta: "Практиковать",
    focus_recent_n: "За 7 дней: {n} раз",
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
