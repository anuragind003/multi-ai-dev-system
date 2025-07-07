import { rest } from 'msw';
import { User } from '../../types/User';

const users: User[] = [
  { id: 1, name: 'John Doe' },
  { id: 2, name: 'Jane Doe' }
];

export const handlers = [
  rest.get('/api/users', (req, res, ctx) => {
    return res(ctx.status(200), ctx.json(users));
  })
];