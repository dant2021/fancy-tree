/**
 * Sample TypeScript file for testing extraction.
 */

interface ApiResponse<T> {
    data: T;
    status: number;
    message: string;
}

interface User {
    id: number;
    name: string;
    email: string;
    roles: string[];
}

abstract class BaseService {
    protected apiUrl: string;
    
    constructor(apiUrl: string) {
        this.apiUrl = apiUrl;
    }
    
    abstract getEndpoint(): string;
    
    protected async makeRequest<T>(endpoint: string): Promise<ApiResponse<T>> {
        // Implementation here
        return {} as ApiResponse<T>;
    }
}

class UserService extends BaseService {
    private cache: Map<number, User> = new Map();
    
    getEndpoint(): string {
        return '/api/users';
    }
    
    async getUser(id: number): Promise<User | null> {
        if (this.cache.has(id)) {
            return this.cache.get(id)!;
        }
        
        const response = await this.makeRequest<User>(`/users/${id}`);
        if (response.status === 200) {
            this.cache.set(id, response.data);
            return response.data;
        }
        return null;
    }
    
    async createUser(userData: Omit<User, 'id'>): Promise<boolean> {
        const response = await this.makeRequest<User>('/users');
        return response.status === 201;
    }
    
    clearCache(): void {
        this.cache.clear();
    }
    
    static validateEmail(email: string): boolean {
        return email.includes('@');
    }
}

function formatUserName(user: User): string {
    return `${user.name} (${user.email})`;
}

const calculateAge = (birthYear: number): number => {
    return new Date().getFullYear() - birthYear;
};

export { UserService, formatUserName, calculateAge };
export type { User, ApiResponse };