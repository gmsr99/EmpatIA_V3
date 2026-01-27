import Link from 'next/link';
import { redirect } from 'next/navigation';
import { Pool } from 'pg';
import { auth } from '@/auth';
import { Button } from '@/components/ui/button';
import { Heart, Brain, Users, Sparkles, Star } from 'lucide-react';

const pool = new Pool({
  host: process.env.POSTGRES_HOST,
  port: parseInt(process.env.POSTGRES_PORT || '5433'),
  user: process.env.POSTGRES_USER,
  password: process.env.POSTGRES_PASSWORD,
  database: process.env.POSTGRES_DB,
});

// Ícones e cores para cada categoria
const categoryConfig: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  familia: { icon: Users, color: 'text-pink-400 bg-pink-400/10 border-pink-400/20', label: 'Família' },
  saude: { icon: Heart, color: 'text-red-400 bg-red-400/10 border-red-400/20', label: 'Saúde' },
  hobbies: { icon: Sparkles, color: 'text-yellow-400 bg-yellow-400/10 border-yellow-400/20', label: 'Hobbies' },
  interesses: { icon: Brain, color: 'text-purple-400 bg-purple-400/10 border-purple-400/20', label: 'Interesses' },
  geral: { icon: Star, color: 'text-blue-400 bg-blue-400/10 border-blue-400/20', label: 'Geral' },
};

interface Memory {
  id: number;
  category: string;
  entity_type: string;
  entity_name: string | null;
  content: string;
  importance: number;
  created_at: string;
}

export default async function DashboardPage() {
  const session = await auth();

  if (!session?.user?.email) {
    redirect('/login');
  }

  // Buscar memórias do utilizador
  const client = await pool.connect();
  let memories: Memory[] = [];
  let userProfile = null;

  try {
    // Buscar perfil do utilizador
    const profileRes = await client.query('SELECT * FROM users WHERE email = $1', [session.user.email]);
    if (profileRes.rows.length > 0) {
      userProfile = profileRes.rows[0];
    }

    // Buscar memórias da tabela user_memories
    const memoriesRes = await client.query(
      `SELECT id, category, entity_type, entity_name, content, importance, created_at
       FROM user_memories
       WHERE user_id = $1 AND is_active = true
       ORDER BY importance DESC, created_at DESC`,
      [session.user.email]
    );
    memories = memoriesRes.rows;
  } catch (e) {
    console.error('Erro ao buscar dados:', e);
  } finally {
    client.release();
  }

  // Agrupar memórias por categoria
  const memoriesByCategory = memories.reduce((acc, memory) => {
    const cat = memory.category || 'geral';
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(memory);
    return acc;
  }, {} as Record<string, Memory[]>);

  return (
    <div className="min-h-screen px-6 pt-24 pb-12">
      <div className="mx-auto max-w-5xl space-y-8">
        {/* Header Section */}
        <div className="flex flex-col justify-between gap-4 border-b border-white/10 pb-6 md:flex-row md:items-center">
          <div>
            <h1 className="text-3xl font-bold text-white">Área de Cliente</h1>
            <p className="mt-1 text-white/60">Bem-vindo de volta, {session.user.name}</p>
          </div>
          <Link href="/#voice-agent">
            <Button className="bg-brand-signature hover:bg-brand-signature/90 rounded-full text-white">
              Falar com EmpatIA
            </Button>
          </Link>
        </div>

        {/* Account Info Card */}
        <div className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-md">
          <h2 className="mb-4 text-xl font-semibold text-white">Dados da Conta</h2>
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <span className="block text-xs font-medium tracking-wider text-white/40 uppercase">
                Nome
              </span>
              <span className="text-white/90">{session.user.name}</span>
            </div>
            <div>
              <span className="block text-xs font-medium tracking-wider text-white/40 uppercase">
                Email
              </span>
              <span className="text-white/90">{session.user.email}</span>
            </div>
            <div>
              <span className="block text-xs font-medium tracking-wider text-white/40 uppercase">
                Memórias Guardadas
              </span>
              <span className="text-white/90">{memories.length}</span>
            </div>
          </div>
        </div>

        {/* Memories Section */}
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-semibold text-white">Memórias da EmpatIA</h2>
            <span className="text-sm text-white/40">
              A EmpatIA lembra-se de si
            </span>
          </div>

          {memories.length === 0 ? (
            <div className="rounded-2xl border border-white/10 bg-white/5 p-12 text-center backdrop-blur-md">
              <Brain className="mx-auto h-12 w-12 text-white/20" />
              <h3 className="mt-4 text-lg font-medium text-white/60">
                Ainda sem memórias registadas
              </h3>
              <p className="mt-2 text-sm text-white/40">
                Fale com a EmpatIA para ela começar a conhecê-lo melhor!
              </p>
              <Link href="/#voice-agent" className="mt-6 inline-block">
                <Button className="bg-brand-signature hover:bg-brand-signature/90 rounded-full text-white">
                  Iniciar Conversa
                </Button>
              </Link>
            </div>
          ) : (
            <div className="grid gap-6 md:grid-cols-2">
              {Object.entries(memoriesByCategory).map(([category, categoryMemories]) => {
                const config = categoryConfig[category] || categoryConfig.geral;
                const Icon = config.icon;

                return (
                  <div
                    key={category}
                    className={`rounded-2xl border ${config.color} p-5 backdrop-blur-md`}
                  >
                    <div className="mb-4 flex items-center gap-3">
                      <div className={`rounded-full p-2 ${config.color}`}>
                        <Icon className="h-5 w-5" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-white">{config.label}</h3>
                        <span className="text-xs text-white/40">
                          {categoryMemories.length} memória{categoryMemories.length !== 1 ? 's' : ''}
                        </span>
                      </div>
                    </div>

                    <div className="space-y-3">
                      {categoryMemories.map((memory) => (
                        <div
                          key={memory.id}
                          className="rounded-xl border border-white/5 bg-black/20 p-3"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex-1">
                              {memory.entity_name && (
                                <span className="mb-1 inline-block rounded-full bg-white/10 px-2 py-0.5 text-xs font-medium text-white/70">
                                  {memory.entity_type}: {memory.entity_name}
                                </span>
                              )}
                              <p className="text-sm text-white/80">{memory.content}</p>
                            </div>
                            <div className="flex items-center gap-1">
                              {[...Array(Math.min(memory.importance, 5))].map((_, i) => (
                                <Star
                                  key={i}
                                  className="h-3 w-3 fill-yellow-400 text-yellow-400"
                                />
                              ))}
                            </div>
                          </div>
                          <span className="mt-2 block text-xs text-white/30">
                            {new Date(memory.created_at).toLocaleDateString('pt-PT', {
                              day: 'numeric',
                              month: 'short',
                              year: 'numeric',
                            })}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
