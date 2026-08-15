use argon2::{Argon2, PasswordHasher, PasswordHash, PasswordVerifier};
use argon2::password_hash::{
    rand_core::OsRng, PasswordHashString, SaltString
};
use jsonwebtoken::{decode, encode, DecodingKey, EncodingKey, Header, Validation};
use serde::{Deserialize, Serialize};
use std::time::{SystemTime, UNIX_EPOCH};
use uuid::Uuid;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Claims {
    pub sub: String,
    pub user_id: String,
    pub exp: u64,
    pub iat: u64,
    pub role: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct User {
    pub id: String,
    pub username: String,
    pub email: String,
    pub password_hash: String,
    pub role: String,
    pub is_active: bool,
    pub created_at: u64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct LoginRequest {
    pub username: String,
    pub password: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct LoginResponse {
    pub access_token: String,
    pub refresh_token: String,
    pub user_id: String,
    pub expires_in: u64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct RegisterRequest {
    pub username: String,
    pub email: String,
    pub password: String,
}

pub struct AuthManager {
    jwt_secret: String,
    token_expiry: u64,
}

impl AuthManager {
    pub fn new(jwt_secret: String, token_expiry_seconds: u64) -> Self {
        AuthManager {
            jwt_secret,
            token_expiry: token_expiry_seconds,
        }
    }

    pub fn hash_password(&self, password: &str) -> Result<String, String> {
        let salt = SaltString::generate(OsRng);
        let argon2 = Argon2::default();
        
        match argon2.hash_password(password.as_bytes(), &salt) {
            Ok(password_hash) => Ok(password_hash.to_string()),
            Err(_) => Err("Failed to hash password".to_string()),
        }
    }

    pub fn verify_password(&self, password: &str, hash: &str) -> Result<bool, String> {
        let parsed_hash = match PasswordHash::new(hash) {
            Ok(h) => h,
            Err(_) => return Err("Invalid password hash format".to_string()),
        };

        let argon2 = Argon2::default();
        match argon2.verify_password(password.as_bytes(), &parsed_hash) {
            Ok(_) => Ok(true),
            Err(_) => Ok(false),
        }
    }

    pub fn generate_tokens(
        &self,
        user_id: &str,
        username: &str,
        role: &str,
    ) -> Result<(String, String), String> {
        let now = SystemTime::now()
           .duration_since(UNIX_EPOCH)
           .map_err(|_| "Time error".to_string())?
           .as_secs();

        let access_claims = Claims {
            sub: username.to_string(),
            user_id: user_id.to_string(),
            exp: now + self.token_expiry,
            iat: now,
            role: role.to_string(),
        };

        let refresh_claims = Claims {
            sub: username.to_string(),
            user_id: user_id.to_string(),
            exp: now + (self.token_expiry * 7),
            iat: now,
            role: "refresh".to_string(),
        };

        let encoding_key = EncodingKey::from_secret(self.jwt_secret.as_bytes());

        let access_token = encode(&Header::default(), &access_claims, &encoding_key)
           .map_err(|_| "Failed to encode access token".to_string())?;

        let refresh_token = encode(&Header::default(), &refresh_claims, &encoding_key)
           .map_err(|_| "Failed to encode refresh token".to_string())?;

        Ok((access_token, refresh_token))
    }

    pub fn verify_token(&self, token: &str) -> Result<Claims, String> {
        let decoding_key = DecodingKey::from_secret(self.jwt_secret.as_bytes());
        
        decode::<Claims>(token, &decoding_key, &Validation::default())
           .map(|data| data.claims)
           .map_err(|_| "Invalid or expired token".to_string())
    }

    pub fn create_user(
        &self,
        username: &str,
        email: &str,
        password: &str,
        role: &str,
    ) -> Result<User, String> {
        let password_hash = self.hash_password(password)?;
        let user_id = Uuid::new_v4().to_string();
        let now = SystemTime::now()
           .duration_since(UNIX_EPOCH)
           .map_err(|_| "Time error".to_string())?
           .as_secs();

        Ok(User {
            id: user_id,
            username: username.to_string(),
            email: email.to_string(),
            password_hash,
            role: role.to_string(),
            is_active: true,
            created_at: now,
        })
    }

    pub fn authenticate_user(
        &self,
        user: &User,
        password: &str,
    ) -> Result<LoginResponse, String> {
        if !user.is_active {
            return Err("User account is inactive".to_string());
        }

        let password_valid = self.verify_password(password, &user.password_hash)?;
        if !password_valid {
            return Err("Invalid credentials".to_string());
        }

        let (access_token, refresh_token) =
            self.generate_tokens(&user.id, &user.username, &user.role)?;

        Ok(LoginResponse {
            access_token,
            refresh_token,
            user_id: user.id.clone(),
            expires_in: self.token_expiry,
        })
    }

    pub fn validate_authorization(
        &self,
        token: &str,
        required_role: &str,
    ) -> Result<Claims, String> {
        let claims = self.verify_token(token)?;
        
        if claims.role != required_role && required_role != "*" {
            return Err("Insufficient permissions".to_string());
        }

        Ok(claims)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_password_hashing() {
        let auth = AuthManager::new("test_secret".to_string(), 3600);
        let password = "SecurePassword123!";
        
        let hash = auth.hash_password(password).unwrap();
        assert!(auth.verify_password(password, &hash).unwrap());
        assert!(!auth.verify_password("WrongPassword", &hash).unwrap());
    }

    #[test]
    fn test_token_generation() {
        let auth = AuthManager::new("test_secret".to_string(), 3600);
        let (access_token, refresh_token) =
            auth.generate_tokens("user123", "testuser", "admin").unwrap();
        
        assert!(!access_token.is_empty());
        assert!(!refresh_token.is_empty());
    }

    #[test]
    fn test_token_verification() {
        let auth = AuthManager::new("test_secret".to_string(), 3600);
        let (access_token, _) =
            auth.generate_tokens("user123", "testuser", "admin").unwrap();
        
        let claims = auth.verify_token(&access_token).unwrap();
        assert_eq!(claims.user_id, "user123");
        assert_eq!(claims.role, "admin");
    }

    #[test]
    fn test_user_creation() {
        let auth = AuthManager::new("test_secret".to_string(), 3600);
        let user = auth
           .create_user("testuser", "test@example.com", "SecurePass123!", "user")
           .unwrap();
        
        assert_eq!(user.username, "testuser");
        assert_eq!(user.email, "test@example.com");
        assert!(user.is_active);
    }

    #[test]
    fn test_authentication() {
        let auth = AuthManager::new("test_secret".to_string(), 3600);
        let user = auth
           .create_user("testuser", "test@example.com", "SecurePass123!", "user")
           .unwrap();
        
        let response = auth.authenticate_user(&user, "SecurePass123!").unwrap();
        assert_eq!(response.user_id, user.id);
        assert!(!response.access_token.is_empty());
    }

    #[test]
    fn test_authorization() {
        let auth = AuthManager::new("test_secret".to_string(), 3600);
        let (token, _) = auth.generate_tokens("user123", "testuser", "admin").unwrap();
        
        let result = auth.validate_authorization(&token, "admin");
        assert!(result.is_ok());
        
        let result = auth.validate_authorization(&token, "user");
        assert!(result.is_err());
    }
}

fn main() {
    println!("Secure Authentication System initialized");
    println!("Features:");
    println!("  - Argon2 password hashing");
    println!("  - JWT token generation and verification");
    println!("  - Role-based access control (RBAC)");
    println!("  - Secure user authentication");
    println!("  - Token expiration and refresh");
}