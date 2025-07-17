import { GoogleGenAI, Chat, Type } from "@google/genai";
import { Product, ChatMessage } from '../types';

if (!process.env.API_KEY) {
  throw new Error("API_KEY environment variable is not set.");
}

const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

const systemInstruction = `
You are a friendly and helpful assistant for EcoHaul, a hyperlocal sustainable goods delivery service.
Your goal is to provide tips and advice on sustainable living.
You can suggest types of products we might carry (like 'zero-waste shampoo bars' or 'local organic honey') but do not invent specific product names or prices.
Keep your answers concise, encouraging, and easy to understand for someone new to sustainability.
Do not use markdown formatting.
`;

export const chatService = (() => {
  let chat: Chat | null = null;

  const getChat = () => {
    if (!chat) {
      chat = ai.chats.create({
        model: 'gemini-2.5-flash',
        config: {
          systemInstruction: systemInstruction,
          thinkingConfig: { thinkingBudget: 0 } // For low latency
        },
        history: [],
      });
    }
    return chat;
  };

  const sendMessage = async (
    message: string,
    onChunk: (text: string) => void,
  ): Promise<void> => {
    try {
      const chatInstance = getChat();
      const stream = await chatInstance.sendMessageStream({ message });
      for await (const chunk of stream) {
        onChunk(chunk.text);
      }
    } catch (error) {
      console.error("Error sending message to Gemini:", error);
      onChunk("Sorry, I'm having trouble connecting right now. Please try again later.");
    }
  };

  const resetChat = () => {
    chat = null;
  };

  return { sendMessage, resetChat };
})();


const generateProductsSchema = {
    type: Type.ARRAY,
    items: {
      type: Type.OBJECT,
      properties: {
        id: {
          type: Type.STRING,
          description: "A unique identifier for the product, e.g., 'prod-1'."
        },
        name: {
          type: Type.STRING,
          description: "The name of the product."
        },
        vendor: {
          type: Type.STRING,
          description: "The name of the local vendor or farm."
        },
        price: {
          type: Type.STRING,
          description: "The price of the product in Indian Rupees, formatted as '₹XXX'."
        },
        category: {
          type: Type.STRING,
          description: "A category like 'Produce', 'Personal Care', 'Household', 'Fashion', or 'Food'."
        },
        tags: {
          type: Type.ARRAY,
          items: {
            type: Type.STRING,
          },
          description: "Two or three relevant tags like 'Organic', 'Handmade', 'Zero-Waste', etc."
        }
      },
      required: ["id", "name", "vendor", "price", "category", "tags"]
    }
};

const generateImage = async (prompt: string): Promise<string> => {
    try {
        const response = await ai.models.generateImages({
            model: 'imagen-3.0-generate-002',
            prompt: prompt,
            config: {
              numberOfImages: 1,
              outputMimeType: 'image/jpeg',
              aspectRatio: '4:3',
            },
        });
        
        const base64ImageBytes: string = response.generatedImages[0].image.imageBytes;
        return `data:image/jpeg;base64,${base64ImageBytes}`;
    } catch (error) {
        console.error(`Error generating image for prompt "${prompt}":`, error);
        // Return a fallback placeholder if image generation fails
        return 'https://images.unsplash.com/photo-1587049352851-d48e0d133413?w=400&h=300&fit=crop';
    }
};

export const generateProducts = async (): Promise<Product[]> => {
    try {
        const prompt = `
            Generate a list of exactly 6 unique, creative, and sustainable product ideas that would be popular in a hyperlocal market in a trendy, eco-conscious neighborhood in Bangalore, India.
            For each product, provide all the fields specified in the schema.
            The product names and vendors should sound authentic for the Bangalore area.
            The prices should be in Indian Rupees (₹).
        `;

        const response = await ai.models.generateContent({
            model: "gemini-2.5-flash",
            contents: prompt,
            config: {
                responseMimeType: "application/json",
                responseSchema: generateProductsSchema,
            },
        });
        
        const responseText = response.text.trim();
        const productsJson = JSON.parse(responseText);

        if (!Array.isArray(productsJson) || productsJson.length === 0) {
            throw new Error("Generated data is not a valid product array.");
        }

        const productsWithoutImages: Omit<Product, 'imageUrl'>[] = productsJson;

        // Generate images in parallel
        const imagePromises = productsWithoutImages.map(product => {
            const imagePrompt = `A high-quality, professional product photograph of "${product.name}", a type of ${product.category}. The product is from a local vendor in Bangalore, India. The style should be clean, bright, and minimalist, suitable for an e-commerce website focused on sustainability.`;
            return generateImage(imagePrompt);
        });

        const imageUrls = await Promise.all(imagePromises);

        // Combine product data with generated images
        const productsWithImages = productsWithoutImages.map((product, index) => ({
            ...product,
            imageUrl: imageUrls[index],
        }));
        
        return productsWithImages as Product[];

    } catch (error) {
        console.error("Error generating products with Gemini:", error);
        throw new Error("Failed to generate sustainable product ideas. Please try again later.");
    }
};
