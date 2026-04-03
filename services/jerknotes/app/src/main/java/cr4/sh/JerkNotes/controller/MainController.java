package cr4.sh.JerkNotes.controller;


import cr4.sh.JerkNotes.config.MyUserDetails;
import cr4.sh.JerkNotes.service.UserService;
import lombok.AllArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.*;
import org.springframework.ui.Model;

@Controller
@RequestMapping("/")
@AllArgsConstructor
public class MainController {
    private final UserService userService;

    // @GetMapping
    // public String GetMain(Model model){
    //     Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
    //     MyUserDetails userDetails = (MyUserDetails) authentication.getPrincipal();
    //     model.addAttribute("username", userDetails.getUsername());
    //     return "main";
    // }

    @GetMapping
    public String root(Model model){
        return "redirect:/profile";
    }

    @GetMapping("profile")
    public String profile(Model model){
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        MyUserDetails userDetails = (MyUserDetails) authentication.getPrincipal();
        model.addAttribute("username", userDetails.getUsername());
        model.addAttribute("userId", userDetails.getUserId());
        return "profile";
    }

    @GetMapping("profile/files")
    public String files(){
        return "files";
    }

    @GetMapping("profile/notes")
    public String notes(){
        return "notes";
    }

    @GetMapping("profile/notes/{id}")
    public String note(@PathVariable String id, Model model){
        model.addAttribute("noteId", id);
        return "note";
    }

    @GetMapping("profile/notes/create")
    public String create(){
        return "create_note";
    }

    @PostMapping("notes/create")
    public String createNote(@RequestParam String title, @RequestParam String content, Model model){
        // Здесь будет логика создания заметки
        return "redirect:/profile/notes";
    }

}
