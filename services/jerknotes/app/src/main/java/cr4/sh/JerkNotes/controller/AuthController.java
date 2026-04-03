package cr4.sh.JerkNotes.controller;


import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;

import cr4.sh.JerkNotes.service.ResetPassword;
import cr4.sh.JerkNotes.service.UserService;
import lombok.AllArgsConstructor;

@Controller
@RequestMapping("/auth")
@AllArgsConstructor
public class AuthController {
    private final UserService userService;
    private final ResetPassword resetPassword;
    private final AuthenticationConfiguration authenticationConfiguration;

    @GetMapping("/register")
    public String showRegistrationForm() {
        return "register"; // Возвращает страницу с формой регистрации
    }

    @PostMapping("/register")
    public String registerUser(@RequestParam String username, @RequestParam String password, Model model, HttpServletRequest request) {
        try {
            userService.registerUser(username, password);
            // Автоматическая аутентификация после регистрации
            UsernamePasswordAuthenticationToken token = new UsernamePasswordAuthenticationToken(username, password);
            Authentication auth = authenticationConfiguration.getAuthenticationManager().authenticate(token);
            SecurityContextHolder.getContext().setAuthentication(auth);
            // Сохраняем SecurityContext в сессии, чтобы аутентификация сохранилась между запросами
            try {
                request.getSession(true).setAttribute("SPRING_SECURITY_CONTEXT", SecurityContextHolder.getContext());
            } catch (Exception ignored) {
                // session could be unavailable in some environments; authentication still present in SecurityContextHolder for this request
            }
            return "redirect:/profile"; // Перенаправляем на профиль сразу
        } catch (Exception e) {
            model.addAttribute("error", "Пользователь уже существует!");
            return "register"; // Показываем ошибку на странице регистрации
        }
    }

    @GetMapping("/login")
    public String showLoginForm() {
        return "login"; // Возвращает страницу с формой регистрации
    }

    @GetMapping("/reset")
    public String resetPassword(Model model) {
        model.addAttribute("notSent", true);
        model.addAttribute("sent", false);
        return "reset";
    }

    @PostMapping("/reset")
    public String processResetRequest(@RequestParam("email") String email, Model model) {
        try {
            resetPassword.SendReset(email);
            model.addAttribute("notSent", false);
            model.addAttribute("sent", true);
            model.addAttribute("email", email);
            return "reset";
        } catch (Exception e) {
            model.addAttribute("notSent", true);
            model.addAttribute("sent", false);
            model.addAttribute("error", "Введенной почты не существует на почте/приложении");
            return "reset";
        }

    }

    @PostMapping("/setpass")
    public String setNewPassword(@RequestParam("email") String email, @RequestParam("resetCode") String resetCode, @RequestParam("newPassword") String newpass, Model model) {
        try {
            if (resetPassword.CheckResetCode(resetCode, email)) {
                try {
                    userService.updatePasswordUser(email, newpass);
                    model.addAttribute("message", "Пароль успешно изменен");
                    model.addAttribute("notSent", false);
                    return "setpass";
                } catch (Exception e) {
                    model.addAttribute("error", "Произошла ошибка");
                    model.addAttribute("notSent", true);
                    return "setpass";
                }    
                

            }
            model.addAttribute("error", "Невалидный код");
            model.addAttribute("notSent", true);
            return "setpass";
        } catch (NumberFormatException e) {
            model.addAttribute("error", "Некорректный ввод");
            model.addAttribute("notSent", true);
            return "setpass";
        }
    }


    @GetMapping("/setpass")
    public String setNewPasswordPage(@RequestParam("email") String email, Model model) {
        model.addAttribute("email", email);
        model.addAttribute("notSent", true);
        return "setpass";
    }



}