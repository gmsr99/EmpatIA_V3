import NextAuth from 'next-auth';
import Credentials from 'next-auth/providers/credentials';
import bcrypt from 'bcryptjs';
import { Pool } from 'pg';

const pool = new Pool({
  host: process.env.POSTGRES_HOST,
  port: parseInt(process.env.POSTGRES_PORT || '5433'),
  user: process.env.POSTGRES_USER,
  password: process.env.POSTGRES_PASSWORD,
  database: process.env.POSTGRES_DB,
  max: 20,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 5000,
});

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Credentials({
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      authorize: async (credentials) => {
        try {
          if (!credentials?.email || !credentials?.password) {
            console.log('Missing credentials');
            return null;
          }

          const email = credentials.email as string;
          const password = credentials.password as string;

          console.log('Attempting login via DB for:', email);

          // Logic to fetch user from DB
          const client = await pool.connect();
          try {
            const res = await client.query('SELECT * FROM users WHERE email = $1', [email]);
            const user = res.rows[0];

            if (!user) {
              console.log('User not found in DB:', email);
              return null;
            }

            const passwordsMatch = await bcrypt.compare(password, user.password);
            if (!passwordsMatch) {
              console.log('Password mismatch for:', email);
              return null;
            }

            console.log('User authenticated successfully:', user.id);
            // Explicitly return the user object with id as string
            return {
              id: String(user.id),
              email: user.email,
              name: user.name,
            };
          } finally {
            client.release();
          }
        } catch (error) {
          console.error('Critical Auth Error:', error);
          return null;
        }
      },
    }),
  ],
  callbacks: {
    async session({ session, user, token }) {
      // With JWT strategy (default for Credentials), user ID is in token.sub
      if (token?.sub) {
        session.user.id = token.sub;
      }
      return session;
    },
    async jwt({ token, user }) {
      if (user) {
        token.sub = user.id;
      }
      return token;
    },
  },
  session: {
    strategy: 'jwt',
  },
  secret: process.env.AUTH_SECRET,
});
