package com.zbank.service;

import com.zbank.model.SupportMessage;
import com.zbank.model.User;
import com.zbank.repository.SupportMessageRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Random;

@Service
@RequiredArgsConstructor
public class SupportService {

    private final SupportMessageRepository supportMessageRepository;
    private static final Random RANDOM = new Random();

    private static final String[] BOT_RESPONSES = {
            "Спасибо за обращение! Мы рассмотрим ваш запрос в ближайшее время.",
            "Здравствуйте! Ваше обращение принято. Номер тикета: #" + System.currentTimeMillis(),
            "Добрый день! Мы ценим ваше обращение. Специалист свяжется с вами в течение 24 часов.",
            "Благодарим за ваше сообщение. Для срочных вопросов звоните 8-800-ZBANK-00.",
            "Ваш вопрос зарегистрирован. Пожалуйста, ожидайте ответа оператора.",
            "Спасибо! Мы уже работаем над вашим запросом. Время ответа — до 2 рабочих часов.",
            "Здравствуйте! Если вопрос касается блокировки карты, позвоните на горячую линию.",
            "Z-Bank благодарит вас за обратную связь! Мы постоянно улучшаем наш сервис.",
            "Ваше обращение передано профильному специалисту. Ожидайте ответа.",
            "Добрый день! Рекомендуем также ознакомиться с разделом FAQ на нашем сайте."
    };

    @Transactional
    public List<SupportMessage> sendMessage(User user, String message) {
        SupportMessage userMsg = SupportMessage.builder()
                .user(user)
                .message(message)
                .isBot(false)
                .build();
        supportMessageRepository.save(userMsg);

        String botResponse = BOT_RESPONSES[RANDOM.nextInt(BOT_RESPONSES.length)];
        SupportMessage botMsg = SupportMessage.builder()
                .user(user)
                .message(botResponse)
                .isBot(true)
                .build();
        supportMessageRepository.save(botMsg);

        return List.of(userMsg, botMsg);
    }

    public List<SupportMessage> getMessages(Long userId) {
        return supportMessageRepository.findByUserIdOrderByCreatedAtAsc(userId);
    }
}
