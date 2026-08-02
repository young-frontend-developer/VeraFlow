# Tilawah — qo‘shimcha izohlar (v5)

Bular v4 ro‘yxatida **yo‘q** bo‘lgan xatolar. Klassik «lahn» tasnifiga solishtirib topildi.

---

# Zaxira izohlar — ro‘yxatda yo‘q xatolar uchun

## 1. GENERIC_LETTER_SUBSTITUTED

**⚑ SHIP FIRST**

*This is the single most valuable entry in the whole registry. It converts every unlisted letter confusion from silence into useful feedback.*

> ### «{word}» — «{expected}» o'rniga «{actual}» aytdingiz.

**▸ Qanday tuzatish**

Bu ikki harf boshqa-boshqa maxrajdan chiqadi. Qaysi so'zda va qaysi harfda xato bo'lganini bildingiz — endi shu harfni alohida, sekin mashq qiling.

Bu xato uchun to'liq izoh hali tayyorlanmagan. Ustozingiz bilan tekshiring.

**▸ Qoida**

Har bir harf o'z maxrajidan chiqishi shart. Bir harfni boshqasiga almashtirish — ochiq xato (lahn jaliy), va u so'z ma'nosini o'zgartirishi mumkin.

**▸ Mashq**

«{expected}» ni alohida 10 marta ayting. So'ng «{word}» so'zini sekin, harf-harf o'qing.

---

## 2. GENERIC_SIFAT_MISMATCH

**⚑ SHIP FIRST**

> ### «{word}» — «{letter}» harfining sifati to'g'ri chiqmadi.

**▸ Qanday tuzatish**

Harfni to'g'ri tanladingiz, lekin uni chiqarish tarzida xato bor.

Bu xato uchun to'liq izoh hali tayyorlanmagan. Ustozingiz bilan tekshiring.

**▸ Qoida**

Harf faqat maxrajidan emas, o'z sifati bilan ham chiqishi kerak — yo'g'onmi ingichkami, jarangli yoki jarangsizmi, kuchli yoki sirg'aluvchimi.

**▸ Mashq**

«{letter}» ni qori o'qishidan eshiting va o'zingiznikini yozib solishtiring.

---

# Harakat va harf xatolari (ochiq xato — eng jiddiy)

## 3. HARAKA_SUBSTITUTED

**⚑ SHIP FIRST**

*Detectable today — the phoneme string carries the vowel. Nothing currently reads it.*

> ### «{word}» — «{letter}» ni {expected} bilan o'qish kerak edi, siz {actual} bilan o'qidingiz.

**▸ Qanday tuzatish**

Harakatni almashtirish — eng jiddiy xato turi, chunki u so'z ma'nosini butunlay o'zgartiradi.

Mushafga qarang va harakatni ko'zingiz bilan tasdiqlang: fatha — ustida, kasra — ostida, zamma — ustida kichik «vov».

**▸ Qoida**

Harakat almashtirish ochiq xato (lahn jaliy) hisoblanadi.

Mashhur misol: «أَنْعَمْتَ» — «ta» fatha bilan («Sen in'om qilding»). Zamma bilan «أَنْعَمْتُ» o'qilsa, ma'no «Men in'om qildim» ga aylanadi — Alloh haqidagi gap o'quvchi haqidagi gapga aylanib qoladi.

**▸ Mashq**

«{word}» ni sekin, har bir harakatni ovoz chiqarib nomlab o'qing: «bu fatha, bu kasra». 5 marta.

---

## 4. HARAKA_TO_SUKUN

> ### «{word}» — «{letter}» harakatli edi, siz sukunli o'qidingiz.

**▸ Qanday tuzatish**

Harfni yutib yubordingiz. Harakatni to'liq ayting — uni tashlab ketmang.

Sekin o'qing: har bir harakatli harf eshitilishi kerak.

**▸ Qoida**

Harakatni sukunga aylantirish ochiq xato hisoblanadi va so'z shaklini buzadi.

**▸ Mashq**

«{word}» ni 5 marta juda sekin o'qing, har bir harakatni to'liq chiqaring.

---

## 5. SUKUN_TO_HARAKA

> ### «{word}» — «{letter}» sukunli edi, siz {actual} qo'shdingiz.

**▸ Qanday tuzatish**

Sukunli harfga unli qo'shib yubordingiz. Harf jim qolishi kerak — undan keyin darhol keyingi harfga o'ting.

Ko'pincha bu qalqala harflarida yuz beradi: tebranish haddan kuchli bo'lsa, u harakatga aylanadi.

**▸ Qoida**

Sukunni harakatga aylantirish ochiq xato hisoblanadi — so'zga mavjud bo'lmagan unli qo'shiladi.

**▸ Mashq**

«{word}» ni 5 marta o'qing, sukunli harfdan keyin hech qanday unli eshitilmasligini tekshiring. Ovozingizni yozib eshiting.

---

## 6. LETTER_DROPPED

> ### «{word}» — «{expected}» harfini tushirib qoldirdingiz.

**▸ Qanday tuzatish**

Harf umuman aytilmadi. Ko'pincha bu tez o'qiganda yuz beradi.

Sekinlashtiring. So'zni harf-harf ayting, keyin normal tezlikda takrorlang.

**▸ Qoida**

Harfni tushirib qoldirish (inqos) ochiq xato hisoblanadi. Bu ayniqsa mad harflarida ko'p uchraydi — «الرَّحْمَـٰن» dagi alif, «الرَّحِيم» dagi yo kabi.

**▸ Mashq**

«{word}» ni harf-harf 5 marta, so'ng butun holda 5 marta o'qing.

---

## 7. LETTER_ADDED

> ### «{word}» — ortiqcha «{actual}» qo'shdingiz.

**▸ Qanday tuzatish**

So'zda yo'q harfni qo'shib yubordingiz. Mushafga qarang va yozilganini aynan o'qing.

Ko'pincha bu ohang uchun yoki odat bo'yicha yuz beradi.

**▸ Qoida**

Harf qo'shish (iydofa) ochiq xato hisoblanadi. Qur'onda nima yozilgan bo'lsa, aynan shu o'qiladi.

**▸ Mashq**

Mushafdan qarab «{word}» ni 5 marta o'qing, har bir harfni ko'zingiz bilan kuzatib.

---

# Yangi harf juftlari

## 8. MAKHARIJ_AIN_TO_GHAYN

> ### «{word}» — «ع» ni «غ» kabi o'qidingiz.

**▸ Qanday tuzatish**

Tovush yuqoriroqdan chiqdi va yo'g'onlashdi. «ع» bo'g'izning o'rtasidan, ingichka chiqadi.

«غ» esa yuqoridan, tomoq tozalayotgandek, va yo'g'on. Yo'g'onlik bor-yo'qligini ushlang.

**▸ Qoida**

«ع» — bo'g'iz o'rtasi, istifola (ingichka). «غ» — bo'g'izning yuqorisi, iste'lo (yo'g'on).

**▸ Mashq**

«عَ — غَ», 10 marta. So'ng «أَنْعَمْتَ» (ع) va «الْمَغْضُوب» (غ).

---

## 9. MAKHARIJ_HHA_TO_KHA

> ### «{word}» — «ح» ni «خ» kabi o'qidingiz.

**▸ Qanday tuzatish**

Tovush yuqoriroqdan chiqdi va yo'g'onlashdi. «ح» pastroqda — bo'g'iz o'rtasida, va ingichka.

«خ» da og'izda qalinlik seziladi, «ح» da yo'q.

**▸ Qoida**

«ح» — bo'g'iz o'rtasi, ingichka. «خ» — bo'g'izning eng yuqorisi, yo'g'on.

**▸ Mashq**

«حَ — خَ», 10 marta. So'ng «الرَّحْمَن» (ح) va «خَوْف» (خ).

---

## 10. MAKHARIJ_HA_TO_HAMZA

> ### «{word}» — «ه» ni «ء» kabi o'qidingiz.

**▸ Qanday tuzatish**

Bo'g'izni yopib yubordingiz. «ه» da bo'g'iz ochiq qoladi — bu shunchaki iliq nafas.

«ء» da esa bo'g'iz to'liq yopiladi va birdan ochiladi.

**▸ Qoida**

Ikkalasi ham bo'g'izning eng chuqur qismidan chiqadi — maxraj bir xil. Farq: «ء» shiddat (to'liq yopiladi), «ه» raxovat (havo uzluksiz).

**▸ Mashq**

«ه» ni 3 soniya cho'zing — cho'ziladi. «ء» ni cho'zib bo'lmaydi. So'ng «هُوَ» va «أَحَد».

---

## 11. MAKHARIJ_SEEN_TO_SHEEN

> ### «{word}» — «{expected}» ni «{actual}» kabi o'qidingiz.

**▸ Qanday tuzatish**

«س» da til uchi tishlarga yaqin, tovush ingichka hushtakka o'xshaydi.

«ش» da til o'rtasi ishlaydi, havo kengroq yoyiladi. Tovush «yassiroq» chiqadi.

**▸ Qoida**

«س» — til uchi va tishlar, sofiyr (hushtak) sifati bilan. «ش» — til o'rtasi va tanglay, tafashshiy (yoyilish) sifati bilan. Maxraj butunlay boshqa.

**▸ Mashq**

«سَ — شَ», 10 marta. So'ng «الْمُسْتَقِيم» (س) va «شَهْر» (ش).

---

## 12. MAKHARIJ_TA_TO_DAL

> ### «{word}» — «{expected}» ni «{actual}» kabi o'qidingiz.

**▸ Qanday tuzatish**

Maxraj bir xil — til uchi tishlar ildizida. Farq ovozda.

Barmog'ingizni tomog'ingizga qo'ying: «د» da titrash bor, «ت» da yo'q, faqat nafas.

**▸ Qoida**

«ت» — mahmus (jarangsiz). «د» — majhur (jarangli). Maxraj bir xil, sifat boshqa.

**▸ Mashq**

Tomoqni ushlab «تَ — دَ», 10 marta. Titrash bor-yo'qligini har safar tekshiring.

---

## 13. MAKHARIJ_LAM_TO_RAA

> ### «{word}» — «{expected}» ni «{actual}» kabi o'qidingiz.

**▸ Qanday tuzatish**

«ل» da til uchi tanglayga tegib turadi, havo yon tomondan o'tadi — takror yo'q.

«ر» da til uchi tebranadi — takror sifati bor. Shu tebranish bor-yo'qligini ushlang.

**▸ Qoida**

«ر» ning o'ziga xos sifati — takror (tebranish). «ل» da bunday tebranish yo'q.

**▸ Mashq**

«لَ — رَ», 10 marta. «ر» da til uchi tebrayaptimi — seziting.

---

## 14. MAKHARIJ_BA_TO_MEEM

> ### «{word}» — «{expected}» ni «{actual}» kabi o'qidingiz.

**▸ Qanday tuzatish**

Ikkalasi ham lab-lab tovushi. Farq burunda.

Burun qanotlarini ushlang: «م» da titrash bor (g'unna), «ب» da yo'q.

**▸ Qoida**

«م» g'unnali — tovush burun bo'shlig'idan ham o'tadi. «ب» da g'unna yo'q, u shiddat harfi va qalqalali.

**▸ Mashq**

Burnini ushlab «بَ — مَ», 10 marta. Titrash qaysi birida borligini tekshiring.

---

## 15. MAKHARIJ_NUN_TO_LAM

> ### «{word}» — «{expected}» ni «{actual}» kabi o'qidingiz.

**▸ Qanday tuzatish**

Maxrajlari yaqin — ikkalasi ham til uchi va tanglay. Farq burunda.

Burun qanotlarini ushlang: «ن» da titrash bor, «ل» da yo'q.

**▸ Qoida**

«ن» g'unnali — burun ishtirok etadi. «ل» da g'unna yo'q, havo tilning yon tomonidan o'tadi.

**▸ Mashq**

Burnini ushlab «نَ — لَ», 10 marta.

---

## 16. MAKHARIJ_JEEM_TO_YA

> ### «{word}» — «{expected}» ni «{actual}» kabi o'qidingiz.

**▸ Qanday tuzatish**

Maxraj bir xil — til o'rtasi va tanglay. Farq kuchda.

«ج» da til tanglayga qattiq tegadi va tovush kuch bilan ochiladi — cho'zib bo'lmaydi. «ي» sirg'alib chiqadi — cho'ziladi.

**▸ Qoida**

«ج» — shiddat harfi, to'liq yopiladi. «ي» — raxovat, havo uzluksiz.

**▸ Mashq**

«ج» ni cho'zishga urinib ko'ring — cho'zilmaydi. «ي» ni cho'zing — cho'ziladi. So'ng «جَعَلَ» va «يَعْلَم».

---

## 17. MAKHARIJ_KAF_TO_QAF

> ### «{word}» — «ك» ni «ق» kabi o'qidingiz.

**▸ Qanday tuzatish**

Til orqaroqdan tegdi va tovush yo'g'onlashdi. «ك» oldinroqda va ingichka.

Tilingizni biroz oldinga suring, og'izdagi qalinlikni tashlang.

**▸ Qoida**

«ك» — istifola (ingichka), «ق» dan biroz oldinroq. «ق» — iste'lo (yo'g'on), tilning eng orqasi.

«كَلْب» (it) va «قَلْب» (yurak).

**▸ Mashq**

«كَ — قَ», 10 marta. So'ng «كُلْ» va «قُلْ».

---

## 18. MAKHARIJ_SAD_TO_ZAY

*Documented error type in the المغظوب family.*

> ### «{word}» — «ص» ni «ز» kabi o'qidingiz.

**▸ Qanday tuzatish**

Ikki narsa birdan buzildi: ovoz qo'shildi va yo'g'onlik yo'qoldi.

«ص» jarangsiz — tomoqda titrash bo'lmasligi kerak. Va tilning orqasi ko'tarilishi kerak.

**▸ Qoida**

«ص» — mahmus (jarangsiz) va iste'lo (yo'g'on). «ز» — majhur (jarangli) va istifola (ingichka). Ikki sifat ham qarama-qarshi.

**▸ Mashq**

Tomoqni ushlab «صَ — زَ», 10 marta. «ص» da titrash yo'qligini va og'izda qalinlik borligini birga tekshiring.

---

## 19. MAKHARIJ_DAD_TO_ZAY

*Documented — the المغظوب / المغزوب family of Fatiha errors.*

> ### «{word}» — «ض» ni «ز» kabi o'qidingiz.

**▸ Qanday tuzatish**

«ض» tilning YON qismidan chiqadi, til uchidan emas. Va u yo'g'on.

Tilingizning yon qismini yuqori oziq tishlarga bosing. «ز» da esa til uchi ishlaydi va tovush ingichka.

**▸ Qoida**

«ض» — yon tomondan, iste'lo, itbaqli, istitolali. «ز» — til uchi, ingichka, sofiyrli.

«الْمَغْضُوب» ni «الْمَغْزُوب» deb o'qish keng tarqalgan xato.

**▸ Mashq**

Til yonini tishga bosib «ضَ», 10 marta. So'ng «زَ» bilan solishtiring. «الْمَغْضُوب» ni sekin 10 marta.

---

## 20. MAKHARIJ_ZAY_TO_SEEN

> ### «{word}» — «{expected}» ni «{actual}» kabi o'qidingiz.

**▸ Qanday tuzatish**

Maxraj bir xil — til uchi va tishlar. Farq ovozda.

Barmog'ingizni tomog'ingizga qo'ying: «ز» da titrash bor, «س» da yo'q.

**▸ Qoida**

«س» — mahmus (jarangsiz), «ز» — majhur (jarangli). Ikkalasida ham sofiyr sifati bor.

**▸ Mashq**

Tomoqni ushlab «سَ — زَ», 10 marta.

---

# Yangi sifat xatolari

## 21. QALQALAH_ON_WRONG_LETTER

*Documented common error — qalqala performed on ع in «الْمَغْضُوبِ عَلَيْهِمْ».*

> ### «{word}» — «{letter}» qalqala harfi emas, unga tebranish qo'shmang.

**▸ Qanday tuzatish**

Sukunli harfni tebratdingiz, lekin bu harf qalqala harflaridan emas.

Uni jim, tebranishsiz qoldiring va darhol keyingi harfga o'ting.

**▸ Qoida**

Qalqala harflari faqat beshta: ق ط ب ج د. Boshqa harflarga tebranish qo'shish xato.

Keng tarqalgan xato: «الْمَغْضُوبِ عَلَيْهِمْ» da «ع» ga qalqala qilish.

**▸ Mashq**

«{word}» ni 10 marta, sukunli harfni butunlay jim qoldirib o'qing.

---

## 22. LAM_TAFKHEEM_WRONG

*Documented anticipatory error — ل read heavy in «وَلَا الضَّالِّينَ» because the mouth is preparing for ض.*

> ### «{word}» — «lom» ingichka o'qilishi kerak edi.

**▸ Qanday tuzatish**

Keyingi yo'g'on harfga tayyorgarlik ko'rib, «lom» ni ham yo'g'on qilib yubordingiz.

Har bir harfni alohida chiqaring. «Lom» aytilib bo'lgach, keyin tilni ko'taring.

**▸ Qoida**

«Lom» faqat «Alloh» ismida, undan oldingi harakat fatha yoki zamma bo'lganda yo'g'on o'qiladi. Qolgan barcha o'rinlarda ingichka.

Keng tarqalgan xato: «وَلَا الضَّالِّينَ» da «lom» ni yo'g'on o'qish — chunki og'iz «ض» ga tayyorlanadi.

**▸ Mashq**

«وَلَا» ni alohida 10 marta ayting — ingichka. So'ng «وَلَا الضَّالِّينَ» ni sekin, «lom» ingichka qolishini kuzatib.

---

**Jami yangi: 22 ta.**  v4 dagi 39 bilan birga — 61 ta izoh.
