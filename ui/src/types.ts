export type Category = {
  id: number;
  name: string;
  description: string;
};

export type CategoryInMessage = {
  id: number;
  name: string;
  description: string;
};

export type Message = {
  id: string;
  subject: string;
  sender: string;
  to: string[];
  snippet?: string;
  body?: string;
  date?: string;
  categories: CategoryInMessage[];
};

export type ClassificationResult = {
  category_id: number;
  category_name: string;
  is_in_category: boolean;
  explanation: string;
};

export type ClassifyResponse = {
  message_id: string;
  classifications: ClassificationResult[];
};
