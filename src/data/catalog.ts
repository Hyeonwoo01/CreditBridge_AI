import type { CatalogCourse, CatalogUnit, SubjectArea, University } from '../lib/types';

/**
 * 편입 희망 대학 교과목 카탈로그 (데모용 샘플).
 * 과목 코드는 실제 대학 체계를 참고했지만 단원 구성·등록금은 예시 값이며
 * 공식 학점 인정 판정을 대신하지 않습니다.
 */

interface Template {
  area: SubjectArea;
  category: 'major' | 'ge';
  description: string;
  units: CatalogUnit[];
  textbooks: string[];
}

const T: Record<string, Template> = {
  calc1: {
    area: 'math',
    category: 'major',
    description: 'Limits, derivatives and their applications, and an introduction to integration.',
    units: [
      {
        name: 'Limits & Continuity',
        nameKo: '극한과 연속',
        keywords: ['limit', 'continuity', 'continuous', 'one-sided limit', 'squeeze theorem', 'limits at infinity', 'asymptote', 'intermediate value theorem', 'epsilon delta'],
      },
      {
        name: 'Derivatives',
        nameKo: '도함수',
        keywords: ['derivative', 'differentiation', 'tangent line', 'rate of change', 'product rule', 'quotient rule', 'chain rule', 'implicit differentiation', 'differentiable'],
      },
      {
        name: 'Applications of Derivatives',
        nameKo: '미분의 응용',
        keywords: ['related rates', 'optimization', 'extrema', 'maximum', 'minimum', 'mean value theorem', 'curve sketching', 'concavity', "l'hopital", 'linear approximation', "newton's method"],
      },
      {
        name: 'Integration',
        nameKo: '적분의 기초',
        keywords: ['antiderivative', 'definite integral', 'indefinite integral', 'riemann sum', 'fundamental theorem of calculus', 'substitution', 'area under'],
      },
    ],
    textbooks: ['Stewart', 'Thomas', 'Larson', 'Briggs', 'OpenStax Calculus'],
  },
  calc2: {
    area: 'math',
    category: 'major',
    description: 'Techniques and applications of integration, sequences and infinite series.',
    units: [
      {
        name: 'Techniques of Integration',
        nameKo: '적분 기법',
        keywords: ['integration by parts', 'trigonometric substitution', 'partial fraction', 'improper integral', 'trigonometric integral', 'numerical integration'],
      },
      {
        name: 'Applications of Integration',
        nameKo: '적분의 응용',
        keywords: ['volume', 'arc length', 'surface area', 'work', 'disk', 'washer', 'shell', 'center of mass'],
      },
      {
        name: 'Sequences & Series',
        nameKo: '수열과 급수',
        keywords: ['sequence', 'series', 'convergence', 'divergence', 'ratio test', 'comparison test', 'integral test', 'alternating series', 'power series', 'taylor series', 'maclaurin'],
      },
      {
        name: 'Parametric, Polar & ODE',
        nameKo: '매개변수·극좌표·미분방정식',
        keywords: ['parametric', 'polar coordinates', 'polar curve', 'differential equation', 'separable'],
      },
    ],
    textbooks: ['Stewart', 'Thomas', 'Larson', 'Briggs', 'OpenStax Calculus'],
  },
  linalg: {
    area: 'math',
    category: 'major',
    description: 'Linear systems, matrices, vector spaces, eigenvalues and orthogonality.',
    units: [
      {
        name: 'Linear Systems',
        nameKo: '연립일차방정식',
        keywords: ['system of linear equations', 'linear system', 'gaussian elimination', 'row reduction', 'echelon form', 'augmented matrix'],
      },
      {
        name: 'Matrix Algebra',
        nameKo: '행렬 대수',
        keywords: ['matrix multiplication', 'inverse', 'determinant', 'transpose', 'lu factorization', 'matrix'],
      },
      {
        name: 'Vector Spaces',
        nameKo: '벡터공간',
        keywords: ['vector space', 'subspace', 'span', 'linear independence', 'basis', 'dimension', 'rank', 'null space', 'column space', 'linear transformation'],
      },
      {
        name: 'Eigenvalues & Orthogonality',
        nameKo: '고윳값과 직교성',
        keywords: ['eigenvalue', 'eigenvector', 'diagonalization', 'characteristic polynomial', 'orthogonal', 'gram-schmidt', 'least squares', 'inner product'],
      },
    ],
    textbooks: ['Lay', 'Strang', 'Anton', 'Axler'],
  },
  chem1: {
    area: 'science',
    category: 'major',
    description: 'Atomic structure, stoichiometry, chemical bonding, gases and thermochemistry.',
    units: [
      {
        name: 'Stoichiometry',
        nameKo: '화학량론',
        keywords: ['mole', 'stoichiometry', 'chemical equation', 'limiting reagent', 'limiting reactant', 'molar mass', 'empirical formula', 'percent yield'],
      },
      {
        name: 'Atomic Structure',
        nameKo: '원자 구조',
        keywords: ['atomic structure', 'quantum', 'electron configuration', 'periodic table', 'orbital', 'periodic trend'],
      },
      {
        name: 'Chemical Bonding',
        nameKo: '화학 결합',
        keywords: ['chemical bond', 'ionic', 'covalent', 'lewis structure', 'vsepr', 'molecular geometry', 'hybridization', 'polarity', 'intermolecular'],
      },
      {
        name: 'Gases & Thermochemistry',
        nameKo: '기체와 열화학',
        keywords: ['gas law', 'ideal gas', 'kinetic molecular', 'thermochemistry', 'enthalpy', 'calorimetry', "hess's law"],
      },
    ],
    textbooks: ['Zumdahl', 'Central Science', 'Tro', 'OpenStax Chemistry', 'Chang'],
  },
  phys1: {
    area: 'science',
    category: 'major',
    description: 'Calculus-based mechanics: kinematics, forces, energy, momentum and rotation.',
    units: [
      {
        name: 'Kinematics',
        nameKo: '운동학',
        keywords: ['kinematics', 'displacement', 'velocity', 'acceleration', 'projectile', 'motion in one dimension', 'vector'],
      },
      {
        name: "Newton's Laws",
        nameKo: '뉴턴 법칙',
        keywords: ["newton's law", 'force', 'friction', 'free body diagram', 'circular motion', 'tension'],
      },
      {
        name: 'Energy & Momentum',
        nameKo: '에너지와 운동량',
        keywords: ['work', 'kinetic energy', 'potential energy', 'conservation of energy', 'momentum', 'impulse', 'collision'],
      },
      {
        name: 'Rotation & Oscillation',
        nameKo: '회전과 진동',
        keywords: ['rotation', 'torque', 'angular momentum', 'moment of inertia', 'rolling', 'oscillation', 'simple harmonic', 'gravitation'],
      },
    ],
    textbooks: ['Halliday', 'Serway', 'University Physics', 'Giancoli', 'Knight'],
  },
  cs1: {
    area: 'cs',
    category: 'major',
    description: 'Introduction to programming: control flow, functions, recursion and data abstraction.',
    units: [
      {
        name: 'Programming Basics',
        nameKo: '프로그래밍 기초',
        keywords: ['variable', 'expression', 'data type', 'operator', 'input', 'python', 'programming'],
      },
      {
        name: 'Control Flow',
        nameKo: '제어 구조',
        keywords: ['conditional', 'if statement', 'loop', 'while loop', 'for loop', 'boolean', 'iteration'],
      },
      {
        name: 'Functions & Recursion',
        nameKo: '함수와 재귀',
        keywords: ['function', 'parameter', 'return value', 'scope', 'recursion', 'higher-order function', 'lambda'],
      },
      {
        name: 'Data & Objects',
        nameKo: '자료형과 객체',
        keywords: ['list', 'string', 'dictionary', 'tuple', 'file', 'object-oriented', 'class', 'exception'],
      },
    ],
    textbooks: ['Think Python', 'Starting Out with Python', 'Zelle', 'Composing Programs', 'Automate the Boring Stuff'],
  },
  ds: {
    area: 'cs',
    category: 'major',
    description: 'Abstract data types, asymptotic analysis, trees, hashing, sorting and graphs.',
    units: [
      {
        name: 'Algorithm Analysis',
        nameKo: '알고리즘 분석',
        keywords: ['big-o', 'asymptotic', 'complexity', 'runtime analysis', 'time complexity'],
      },
      {
        name: 'Linear Structures',
        nameKo: '선형 자료구조',
        keywords: ['linked list', 'stack', 'queue', 'array list', 'dynamic array', 'deque'],
      },
      {
        name: 'Trees & Hashing',
        nameKo: '트리와 해싱',
        keywords: ['binary tree', 'binary search tree', 'balanced tree', 'heap', 'priority queue', 'hash table', 'hashing', 'avl', 'red-black'],
      },
      {
        name: 'Sorting & Graphs',
        nameKo: '정렬과 그래프',
        keywords: ['sorting', 'merge sort', 'quicksort', 'graph', 'breadth-first search', 'depth-first search', 'shortest path'],
      },
    ],
    textbooks: ['Goodrich', 'Weiss', 'Sedgewick', 'Cormen', 'Data Structures and Algorithms'],
  },
  discrete: {
    area: 'math',
    category: 'major',
    description: 'Logic, proofs, sets, counting, probability, number theory and graph theory.',
    units: [
      {
        name: 'Logic & Proofs',
        nameKo: '논리와 증명',
        keywords: ['propositional logic', 'predicate logic', 'quantifier', 'proof', 'induction', 'contradiction', 'truth table'],
      },
      {
        name: 'Sets, Functions & Relations',
        nameKo: '집합·함수·관계',
        keywords: ['set', 'function', 'relation', 'equivalence relation', 'cardinality'],
      },
      {
        name: 'Counting & Probability',
        nameKo: '경우의 수와 확률',
        keywords: ['counting', 'permutation', 'combination', 'pigeonhole', 'binomial', 'probability', 'inclusion-exclusion', 'recurrence'],
      },
      {
        name: 'Number Theory & Graphs',
        nameKo: '정수론과 그래프',
        keywords: ['number theory', 'modular arithmetic', 'divisibility', 'prime', 'gcd', 'graph theory', 'tree', 'rsa'],
      },
    ],
    textbooks: ['Rosen', 'Epp', 'Mathematics for Computer Science'],
  },
  stats: {
    area: 'math',
    category: 'ge',
    description: 'Descriptive statistics, probability, statistical inference and regression.',
    units: [
      {
        name: 'Descriptive Statistics',
        nameKo: '기술통계',
        keywords: ['descriptive statistic', 'mean', 'median', 'standard deviation', 'histogram', 'boxplot', 'sampling'],
      },
      {
        name: 'Probability Models',
        nameKo: '확률 모형',
        keywords: ['probability', 'random variable', 'normal distribution', 'binomial distribution', 'central limit theorem', 'sampling distribution'],
      },
      {
        name: 'Statistical Inference',
        nameKo: '통계적 추론',
        keywords: ['confidence interval', 'hypothesis test', 'p-value', 't-test', 'significance', 'chi-square', 'null hypothesis'],
      },
      {
        name: 'Regression',
        nameKo: '회귀분석',
        keywords: ['correlation', 'linear regression', 'scatterplot', 'least squares', 'residual', 'anova'],
      },
    ],
    textbooks: ['OpenIntro', 'Basic Practice of Statistics', 'Freedman', 'Triola', 'De Veaux'],
  },
  micro: {
    area: 'social',
    category: 'ge',
    description: 'Supply and demand, consumer and firm behavior, market structures and welfare.',
    units: [
      {
        name: 'Supply & Demand',
        nameKo: '수요와 공급',
        keywords: ['supply', 'demand', 'equilibrium', 'elasticity', 'price control', 'price ceiling', 'price floor'],
      },
      {
        name: 'Consumers & Firms',
        nameKo: '소비자와 기업',
        keywords: ['consumer choice', 'utility', 'production', 'cost curve', 'marginal cost', 'opportunity cost'],
      },
      {
        name: 'Market Structures',
        nameKo: '시장 구조',
        keywords: ['perfect competition', 'monopoly', 'oligopoly', 'monopolistic competition', 'game theory'],
      },
      {
        name: 'Welfare & Policy',
        nameKo: '후생과 정책',
        keywords: ['consumer surplus', 'producer surplus', 'externality', 'public good', 'market failure', 'tax', 'deadweight loss'],
      },
    ],
    textbooks: ['Mankiw', 'Krugman', 'OpenStax Microeconomics', 'Case', 'Principles of Microeconomics'],
  },
  macro: {
    area: 'social',
    category: 'ge',
    description: 'National income, growth, money and banking, monetary and fiscal policy.',
    units: [
      {
        name: 'Measuring the Economy',
        nameKo: '거시경제 지표',
        keywords: ['gdp', 'inflation', 'unemployment', 'consumer price index', 'national income'],
      },
      {
        name: 'Long-run Growth',
        nameKo: '장기 성장',
        keywords: ['economic growth', 'productivity', 'saving', 'investment', 'long run'],
      },
      {
        name: 'Money & Monetary Policy',
        nameKo: '화폐와 통화정책',
        keywords: ['money supply', 'central bank', 'federal reserve', 'interest rate', 'monetary policy', 'banking'],
      },
      {
        name: 'Fiscal Policy & Cycles',
        nameKo: '재정정책과 경기변동',
        keywords: ['fiscal policy', 'aggregate demand', 'aggregate supply', 'business cycle', 'government spending', 'multiplier', 'exchange rate'],
      },
    ],
    textbooks: ['Mankiw', 'Krugman', 'OpenStax Macroeconomics', 'Principles of Macroeconomics'],
  },
  psych: {
    area: 'social',
    category: 'ge',
    description: 'Survey of psychology: biological bases, cognition, development, personality and social behavior.',
    units: [
      {
        name: 'Research & Biological Bases',
        nameKo: '연구 방법과 생물학적 기초',
        keywords: ['research method', 'experiment', 'neuron', 'brain', 'nervous system', 'biological psychology'],
      },
      {
        name: 'Perception, Learning & Memory',
        nameKo: '지각·학습·기억',
        keywords: ['sensation', 'perception', 'learning', 'classical conditioning', 'operant conditioning', 'memory', 'cognition'],
      },
      {
        name: 'Development & Personality',
        nameKo: '발달과 성격',
        keywords: ['development', 'personality', 'intelligence', 'motivation', 'emotion'],
      },
      {
        name: 'Social & Clinical',
        nameKo: '사회·임상 심리',
        keywords: ['social psychology', 'psychological disorder', 'therapy', 'stress', 'mental health', 'consciousness'],
      },
    ],
    textbooks: ['Myers', 'OpenStax Psychology', 'Gray', 'Ciccarelli'],
  },
  writing: {
    area: 'humanities',
    category: 'ge',
    description: 'Academic reading and writing: rhetoric, argument, revision and research.',
    units: [
      {
        name: 'Rhetoric & Argument',
        nameKo: '수사학과 논증',
        keywords: ['rhetoric', 'rhetorical analysis', 'audience', 'argument', 'thesis', 'persuasive'],
      },
      {
        name: 'Writing Process',
        nameKo: '글쓰기 과정',
        keywords: ['drafting', 'revision', 'peer review', 'writing process', 'essay'],
      },
      {
        name: 'Research Writing',
        nameKo: '연구 기반 글쓰기',
        keywords: ['research paper', 'source', 'citation', 'mla', 'apa', 'annotated bibliography', 'plagiarism'],
      },
      {
        name: 'Critical Reading',
        nameKo: '비판적 읽기',
        keywords: ['critical reading', 'close reading', 'critical thinking', 'summary', 'analysis'],
      },
    ],
    textbooks: ['They Say', "St. Martin's Guide", "Everything's an Argument", 'Norton Field Guide'],
  },
  bio1: {
    area: 'science',
    category: 'major',
    description: 'Molecules and cells, genetics, and evolution.',
    units: [
      {
        name: 'Chemistry of Life',
        nameKo: '생명의 화학',
        keywords: ['macromolecule', 'protein', 'carbohydrate', 'lipid', 'nucleic acid', 'enzyme'],
      },
      {
        name: 'Cell Biology',
        nameKo: '세포 생물학',
        keywords: ['cell structure', 'membrane', 'organelle', 'membrane transport', 'cellular respiration', 'photosynthesis'],
      },
      {
        name: 'Genetics',
        nameKo: '유전학',
        keywords: ['dna', 'replication', 'transcription', 'translation', 'gene expression', 'mitosis', 'meiosis', 'mendelian', 'inheritance'],
      },
      {
        name: 'Evolution & Ecology',
        nameKo: '진화와 생태',
        keywords: ['evolution', 'natural selection', 'population genetics', 'phylogeny', 'speciation', 'ecology'],
      },
    ],
    textbooks: ['Campbell', 'OpenStax Biology', 'Raven'],
  },
};

type Row = [templateKey: keyof typeof T, code: string, title: string, credits: number];

function build(schoolId: string, rows: Row[]): CatalogCourse[] {
  return rows.map(([key, code, title, credits]) => {
    const t = T[key];
    return {
      id: `${schoolId}:${code}`,
      code,
      title,
      credits,
      area: t.area,
      category: t.category,
      description: t.description,
      units: t.units,
      textbooks: t.textbooks,
    };
  });
}

export const UNIVERSITIES: University[] = [
  {
    id: 'berkeley',
    name: 'UC Berkeley',
    location: 'Berkeley, CA',
    creditLabel: 'units',
    tuitionPerCredit: 1550,
    creditsPerSemester: 15,
    transferCreditCap: 70,
    courses: build('berkeley', [
      ['calc1', 'MATH 1A', 'Calculus', 4],
      ['calc2', 'MATH 1B', 'Calculus', 4],
      ['linalg', 'MATH 54', 'Linear Algebra & Differential Equations', 4],
      ['chem1', 'CHEM 1A', 'General Chemistry', 3],
      ['phys1', 'PHYSICS 7A', 'Physics for Scientists and Engineers', 4],
      ['cs1', 'COMPSCI 61A', 'Structure and Interpretation of Computer Programs', 4],
      ['ds', 'COMPSCI 61B', 'Data Structures', 4],
      ['discrete', 'COMPSCI 70', 'Discrete Mathematics and Probability Theory', 4],
      ['stats', 'STAT 20', 'Introduction to Probability and Statistics', 4],
      ['micro', 'ECON 1', 'Introduction to Economics', 4],
      ['macro', 'ECON 2', 'Introduction to Economics — Lecture Format', 4],
      ['psych', 'PSYCH 1', 'General Psychology', 3],
      ['writing', 'COLWRIT R1A', 'Accelerated Reading and Composition', 4],
      ['bio1', 'BIOLOGY 1A', 'General Biology', 3],
    ]),
  },
  {
    id: 'utaustin',
    name: 'UT Austin',
    location: 'Austin, TX',
    creditLabel: 'hours',
    tuitionPerCredit: 1400,
    creditsPerSemester: 15,
    transferCreditCap: 66,
    courses: build('utaustin', [
      ['calc1', 'M 408C', 'Differential and Integral Calculus', 4],
      ['calc2', 'M 408D', 'Sequences, Series, and Multivariable Calculus', 4],
      ['linalg', 'M 340L', 'Matrices and Matrix Calculations', 3],
      ['chem1', 'CH 301', 'Principles of Chemistry I', 3],
      ['phys1', 'PHY 303K', 'Engineering Physics I', 3],
      ['cs1', 'CS 312', 'Introduction to Programming', 3],
      ['ds', 'CS 314', 'Data Structures', 3],
      ['discrete', 'CS 311', 'Discrete Math for Computer Science', 3],
      ['stats', 'SDS 302', 'Data Analysis for the Health Sciences', 3],
      ['micro', 'ECO 304K', 'Introduction to Microeconomics', 3],
      ['macro', 'ECO 304L', 'Introduction to Macroeconomics', 3],
      ['psych', 'PSY 301', 'Introduction to Psychology', 3],
      ['writing', 'RHE 306', 'Rhetoric and Writing', 3],
      ['bio1', 'BIO 311C', 'Introductory Biology I', 3],
    ]),
  },
  {
    id: 'umich',
    name: 'University of Michigan',
    location: 'Ann Arbor, MI',
    creditLabel: 'credits',
    tuitionPerCredit: 2400,
    creditsPerSemester: 15,
    transferCreditCap: 60,
    courses: build('umich', [
      ['calc1', 'MATH 115', 'Calculus I', 4],
      ['calc2', 'MATH 116', 'Calculus II', 4],
      ['linalg', 'MATH 214', 'Applied Linear Algebra', 4],
      ['chem1', 'CHEM 130', 'General Chemistry: Macroscopic Investigations and Reaction Principles', 3],
      ['phys1', 'PHYSICS 140', 'General Physics I', 4],
      ['cs1', 'EECS 183', 'Elementary Programming Concepts', 4],
      ['ds', 'EECS 280', 'Programming and Introductory Data Structures', 4],
      ['discrete', 'EECS 203', 'Discrete Mathematics', 4],
      ['stats', 'STATS 250', 'Introduction to Statistics and Data Analysis', 4],
      ['micro', 'ECON 101', 'Principles of Economics I', 4],
      ['macro', 'ECON 102', 'Principles of Economics II', 4],
      ['psych', 'PSYCH 111', 'Introduction to Psychology', 4],
      ['writing', 'ENGLISH 125', 'Writing and Academic Inquiry', 4],
      ['bio1', 'BIOLOGY 171', 'Introductory Biology: Ecology and Evolution', 4],
    ]),
  },
];

export function getUniversity(id: string): University {
  return UNIVERSITIES.find((u) => u.id === id) ?? UNIVERSITIES[0];
}
