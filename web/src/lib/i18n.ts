// UI chrome only. Every sentence ABOUT TAJWEED comes from the server, out of
// content/rules.json — never from here and never from an LLM.
//
// Uzbek uses the proper modifier letter ʻ (U+02BB) in oʻ / gʻ, not an
// apostrophe. Russian is written as Russian, not as a translation of the Uzbek.
// Both are first drafts by a developer and want a native pass before launch.
export type Lang = "uz" | "ru";

const STRINGS = {
  uz: {
    // navigation
    nav_practice: "Mashq",
    nav_library: "Oyatlar",
    nav_log: "Yozuvlar",

    // recitation
    listen: "Qori oʻqishini tinglang",
    record: "Oʻqishni boshlash",
    stop: "Toʻxtatish",
    recording_hint: "Shoshilmang. Tinch va sekin oʻqing.",
    waiting: "Tinglanmoqda",
    waiting_hint: "Bir necha soniya kutib turing.",

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

    // correction card
    label_heard: "Nimani eshitdik",
    label_fix: "Qanday tuzatish kerak",
    // The FOUR card slots, in reading order: what happened (the kind title),
    // where, how to fix it, what to practise. `card_why` and the prose drill
    // are gone — a correction is not a tajweed lesson.
    card_where: "Qayerda",
    card_you_said: "Siz aytdingiz",
    card_correct: "Toʻgʻrisi",
    card_fix: "Tuzatish",
    card_practice: "Endi mashq qilamiz",
    // Repeats are merged into one card; this says how many and where.
    card_times: "marta uchradi",
    // Practice audio is the LETTER, not the ayah.
    listen_letter: "Harf tovushini eshitish",
    listen_ayah: "Oyatni qori oʻqishida eshitish",

    // ── the practice ladder. Narrow to wide: the letter alone, the letter
    // with each haraka, the word they misread, then back to the ayah.
    rung_letter: "Faqat shu harf",
    rung_syllables: "Harakatlar bilan",
    rung_word: "Shu soʻz",
    rung_ayah: "Endi oyatni oʻqing",
    rung_record: "Oʻqib koʻrish",
    // Rungs the engine cannot score. Says what to do instead of leaving the
    // rung looking as though its button failed to load.
    rung_say: "Ovoz chiqarib ayting",

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
    nav_practice: "Практика",
    nav_library: "Аяты",
    nav_log: "Записи",

    listen: "Послушайте чтеца",
    record: "Начать чтение",
    stop: "Остановить",
    recording_hint: "Не торопитесь. Читайте спокойно.",
    waiting: "Слушаем",
    waiting_hint: "Это займёт несколько секунд.",

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

    label_heard: "Что мы услышали",
    label_fix: "Как исправить",
    card_where: "Где",
    card_you_said: "Вы сказали",
    card_correct: "Правильно",
    card_fix: "Исправление",
    card_practice: "Теперь потренируемся",
    card_times: "раза встретилось",
    listen_letter: "Послушать звук буквы",
    listen_ayah: "Послушать аят у чтеца",

    rung_letter: "Только эта буква",
    rung_syllables: "С огласовками",
    rung_word: "Это слово",
    rung_ayah: "Теперь весь аят",
    rung_record: "Прочитать",
    rung_say: "Скажите вслух",

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
