/**
 * Sample Java file for testing extraction.
 */

package com.example.services;

import java.util.*;
import java.util.concurrent.CompletableFuture;

public interface UserRepository {
    Optional<User> findById(Long id);
    List<User> findAll();
    User save(User user);
    void deleteById(Long id);
}

public abstract class BaseService<T, ID> {
    protected UserRepository repository;
    
    public BaseService(UserRepository repository) {
        this.repository = repository;
    }
    
    public abstract T findById(ID id);
    
    protected void validateEntity(T entity) {
        if (entity == null) {
            throw new IllegalArgumentException("Entity cannot be null");
        }
    }
}

public class UserService extends BaseService<User, Long> {
    private final EmailService emailService;
    private final Map<Long, User> cache;
    
    public UserService(UserRepository repository, EmailService emailService) {
        super(repository);
        this.emailService = emailService;
        this.cache = new HashMap<>();
    }
    
    @Override
    public User findById(Long id) {
        if (cache.containsKey(id)) {
            return cache.get(id);
        }
        
        Optional<User> user = repository.findById(id);
        user.ifPresent(u -> cache.put(id, u));
        return user.orElse(null);
    }
    
    public CompletableFuture<Boolean> createUserAsync(String name, String email) {
        return CompletableFuture.supplyAsync(() -> {
            try {
                User user = new User(name, email);
                validateEntity(user);
                User saved = repository.save(user);
                emailService.sendWelcomeEmail(saved);
                return true;
            } catch (Exception e) {
                return false;
            }
        });
    }
    
    public List<User> searchUsers(String query, int limit) {
        return repository.findAll()
            .stream()
            .filter(user -> user.getName().contains(query))
            .limit(limit)
            .collect(Collectors.toList());
    }
    
    private void clearCache() {
        cache.clear();
    }
    
    public static class UserBuilder {
        private String name;
        private String email;
        
        public UserBuilder setName(String name) {
            this.name = name;
            return this;
        }
        
        public UserBuilder setEmail(String email) {
            this.email = email;
            return this;
        }
        
        public User build() {
            return new User(name, email);
        }
    }
}

enum UserRole {
    ADMIN("admin"),
    USER("user"),
    GUEST("guest");
    
    private final String value;
    
    UserRole(String value) {
        this.value = value;
    }
    
    public String getValue() {
        return value;
    }
}