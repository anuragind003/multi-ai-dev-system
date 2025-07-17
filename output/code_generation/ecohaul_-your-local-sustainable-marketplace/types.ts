export interface Product {
  id: string;
  name: string;
  vendor: string;
  price: string;
  imageUrl: string;
  category: string;
  tags: string[];
}

export type CartItem = Product & {
  quantity: number;
};

export interface ChatMessage {
  id: string;
  role: 'user' | 'model';
  text: string;
}