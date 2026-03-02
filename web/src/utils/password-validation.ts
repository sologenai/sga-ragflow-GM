export interface PasswordRule {
  key: string;
  label: string;
  test: (password: string, account?: string) => boolean;
}

export const passwordRules: PasswordRule[] = [
  {
    key: 'minLength',
    label: 'password.ruleMinLength',
    test: (p) => p.length >= 8,
  },
  {
    key: 'charTypes',
    label: 'password.ruleCharTypes',
    test: (p) => {
      let count = 0;
      if (/[A-Z]/.test(p)) count++;
      if (/[a-z]/.test(p)) count++;
      if (/[0-9]/.test(p)) count++;
      if (/[^A-Za-z0-9]/.test(p)) count++;
      return count >= 3;
    },
  },
  {
    key: 'noSequential',
    label: 'password.ruleNoSequential',
    test: (p) => !hasConsecutiveSequence(p, 4),
  },
  {
    key: 'noAccount',
    label: 'password.ruleNoAccount',
    test: (p, account) =>
      !account ||
      account.length < 3 ||
      !p.toLowerCase().includes(account.toLowerCase()),
  },
];

function hasConsecutiveSequence(s: string, minLen: number): boolean {
  const lower = s.toLowerCase();
  for (let i = 0; i <= lower.length - minLen; i++) {
    let asc = true,
      desc = true;
    for (let j = 1; j < minLen; j++) {
      if (lower.charCodeAt(i + j) !== lower.charCodeAt(i + j - 1) + 1)
        asc = false;
      if (lower.charCodeAt(i + j) !== lower.charCodeAt(i + j - 1) - 1)
        desc = false;
      if (!asc && !desc) break;
    }
    if (asc || desc) return true;
  }
  return false;
}

export function validatePassword(
  password: string,
  account?: string,
): string | null {
  for (const rule of passwordRules) {
    if (!rule.test(password, account)) {
      return rule.label;
    }
  }
  return null;
}
