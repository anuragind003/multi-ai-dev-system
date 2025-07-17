import { User, Recording } from '../types';

// --- MOCK USERS ---
export const mockUsers: User[] = [
    { id: 'u1', name: 'Anurag Kumar', role: 'Team Leader' },
    { id: 'u2', name: 'Anil Tyagi', role: 'Process Manager' },
];

const userCredentials: Record<string, { password: string, user: User }> = {
    'leader': { password: 'password1', user: mockUsers[0] },
    'manager': { password: 'password2', user: mockUsers[1] },
};

export const getMockUser = (username: string, password: string): User | null => {
    const creds = userCredentials[username];
    if (creds && creds.password === password) {
        return creds.user;
    }
    return null;
}

// --- MOCK RECORDINGS ---
const generateMockRecordings = (): Recording[] => {
    const recordings: Recording[] = [];
    const startDate = new Date();
    startDate.setMonth(startDate.getMonth() - 2); // Go back 2 months

    for (let i = 0; i < 50; i++) {
        const date = new Date(startDate.getTime() + (i * 24 * 3600 * 1000) / 2); // Advance half a day
        
        const pad = (num: number) => num.toString().padStart(2, '0');
        const dateStr = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
        const timeStr = `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
        
        const lanId = `LTF100${pad(i)}`;
        const sizeInBytes = Math.floor(Math.random() * (50 * 1024 * 1024)) + (5 * 1024 * 1024); // 5MB to 50MB
        const size = `${(sizeInBytes / (1024 * 1024)).toFixed(1)} MB`;
        const durationSeconds = Math.floor(Math.random() * 540) + 60; // 1 to 10 minutes
        const callDuration = new Date(durationSeconds * 1000).toISOString().substr(11, 8);
        
        recordings.push({
            lanId: lanId,
            date: dateStr,
            fileName: `${lanId}_${dateStr}.mp4`,
            size: size,
            sizeInBytes: sizeInBytes,
            streamUrl: 'https://storage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4', // Placeholder video
            callDuration: callDuration,
            status: 'APPROVED',
            time: timeStr,
            uploadTime: dateStr,
        });
    }
    return recordings.sort((a,b) => new Date(b.date + ' ' + b.time).getTime() - new Date(a.date + ' ' + a.time).getTime());
};

export const mockRecordings: Recording[] = generateMockRecordings();
