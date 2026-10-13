import type { CatalogCourse, CatalogUnit, SubjectArea, University } from '../lib/types';

/**
 * 편입 희망 대학 교과목 카탈로그 (데모용 샘플).
 * 과목 코드는 실제 대학 체계를 참고했지만 단원 구성·등록금은 예시 값이며
 * 공식 학점 인정 판정을 대신하지 않습니다.
 */

interface Template {
  level: string;
  area: SubjectArea;
  category: 'major' | 'ge';
  description: string;
  units: CatalogUnit[];
  textbooks: string[];
}

const T: Record<string, Template> = {
  calc1: {
    level: 'First-semester calculus for STEM majors (not business/applied calculus).',
    area: 'math',
    category: 'major',
    description: 'Limits, derivatives and their applications, and an introduction to integration.',
    units: [
      {
        name: 'Limits & Continuity',
        objectives: 'Evaluate limits (one-sided, infinite, at infinity) algebraically and graphically; define and test continuity; apply the Intermediate Value Theorem.',
        nameKo: '극한과 연속',
        keywords: ['limit', 'continuity', 'continuous', 'one-sided limit', 'squeeze theorem', 'limits at infinity', 'asymptote', 'intermediate value theorem', 'epsilon delta'],
      },
      {
        name: 'Derivatives',
        objectives: 'Define the derivative as a limit; differentiate polynomial, rational, trigonometric, exponential and logarithmic functions using the product, quotient and chain rules and implicit differentiation.',
        nameKo: '도함수',
        keywords: ['derivative', 'differentiation', 'tangent line', 'rate of change', 'product rule', 'quotient rule', 'chain rule', 'implicit differentiation', 'differentiable'],
      },
      {
        name: 'Applications of Derivatives',
        objectives: 'Solve related-rates and optimization problems; find extrema; use the Mean Value Theorem, concavity and L\'Hopital\'s rule for curve analysis; linear approximation.',
        nameKo: '미분의 응용',
        keywords: ['related rates', 'optimization', 'extrema', 'maximum', 'minimum', 'mean value theorem', 'curve sketching', 'concavity', "l'hopital", 'linear approximation', "newton's method"],
      },
      {
        name: 'Integration',
        objectives: 'Compute antiderivatives; define the definite integral via Riemann sums; apply the Fundamental Theorem of Calculus and u-substitution.',
        nameKo: '적분의 기초',
        keywords: ['antiderivative', 'definite integral', 'indefinite integral', 'riemann sum', 'fundamental theorem of calculus', 'substitution', 'area under'],
      },
    ],
    textbooks: ['Stewart', 'Thomas', 'Larson', 'Briggs', 'OpenStax Calculus'],
  },
  calc2: {
    level: 'Second-semester calculus for STEM majors.',
    area: 'math',
    category: 'major',
    description: 'Techniques and applications of integration, sequences and infinite series.',
    units: [
      {
        name: 'Techniques of Integration',
        objectives: 'Integrate by parts, trigonometric substitution and partial fractions; evaluate improper integrals; numerical integration.',
        nameKo: '적분 기법',
        keywords: ['integration by parts', 'trigonometric substitution', 'partial fraction', 'improper integral', 'trigonometric integral', 'numerical integration'],
      },
      {
        name: 'Applications of Integration',
        objectives: 'Compute areas between curves, volumes of revolution (disk, washer, shell), arc length and physical applications such as work.',
        nameKo: '적분의 응용',
        keywords: ['volume', 'arc length', 'surface area', 'work', 'disk', 'washer', 'shell', 'center of mass'],
      },
      {
        name: 'Sequences & Series',
        objectives: 'Determine convergence of sequences and infinite series with standard tests; represent functions as power series and Taylor/Maclaurin series.',
        nameKo: '수열과 급수',
        keywords: ['sequence', 'series', 'convergence', 'divergence', 'ratio test', 'comparison test', 'integral test', 'alternating series', 'power series', 'taylor series', 'maclaurin'],
      },
      {
        name: 'Parametric, Polar & ODE',
        objectives: 'Work with parametric equations and polar coordinates; solve introductory separable differential equations.',
        nameKo: '매개변수·극좌표·미분방정식',
        keywords: ['parametric', 'polar coordinates', 'polar curve', 'differential equation', 'separable'],
      },
    ],
    textbooks: ['Stewart', 'Thomas', 'Larson', 'Briggs', 'OpenStax Calculus'],
  },
  linalg: {
    level: 'Sophomore-level linear algebra with proofs of basic results.',
    area: 'math',
    category: 'major',
    description: 'Linear systems, matrices, vector spaces, eigenvalues and orthogonality.',
    units: [
      {
        name: 'Linear Systems',
        objectives: 'Solve systems of linear equations by Gaussian elimination and row reduction to echelon form; describe solution sets.',
        nameKo: '연립일차방정식',
        keywords: ['system of linear equations', 'linear system', 'gaussian elimination', 'row reduction', 'echelon form', 'augmented matrix'],
      },
      {
        name: 'Matrix Algebra',
        objectives: 'Perform matrix operations; compute inverses and determinants; use matrix factorizations.',
        nameKo: '행렬 대수',
        keywords: ['matrix multiplication', 'inverse', 'determinant', 'transpose', 'lu factorization', 'matrix'],
      },
      {
        name: 'Vector Spaces',
        objectives: 'Reason about vector spaces and subspaces, span, linear independence, basis, dimension, rank, null and column spaces, and linear transformations.',
        nameKo: '벡터공간',
        keywords: ['vector space', 'subspace', 'span', 'linear independence', 'basis', 'dimension', 'rank', 'null space', 'column space', 'linear transformation'],
      },
      {
        name: 'Eigenvalues & Orthogonality',
        objectives: 'Compute eigenvalues and eigenvectors and diagonalize matrices; use orthogonality, Gram-Schmidt and least squares.',
        nameKo: '고윳값과 직교성',
        keywords: ['eigenvalue', 'eigenvector', 'diagonalization', 'characteristic polynomial', 'orthogonal', 'gram-schmidt', 'least squares', 'inner product'],
      },
    ],
    textbooks: ['Lay', 'Strang', 'Anton', 'Axler'],
  },
  chem1: {
    level: 'First semester of the general chemistry sequence for science majors.',
    area: 'science',
    category: 'major',
    description: 'Atomic structure, stoichiometry, chemical bonding, gases and thermochemistry.',
    units: [
      {
        name: 'Stoichiometry',
        objectives: 'Use the mole concept, balance chemical equations, and perform stoichiometric calculations including limiting reactant and percent yield.',
        nameKo: '화학량론',
        keywords: ['mole', 'stoichiometry', 'chemical equation', 'limiting reagent', 'limiting reactant', 'molar mass', 'empirical formula', 'percent yield'],
      },
      {
        name: 'Atomic Structure',
        objectives: 'Describe quantum-mechanical atomic structure, orbitals and electron configurations, and explain periodic trends.',
        nameKo: '원자 구조',
        keywords: ['atomic structure', 'quantum', 'electron configuration', 'periodic table', 'orbital', 'periodic trend'],
      },
      {
        name: 'Chemical Bonding',
        objectives: 'Explain ionic and covalent bonding, draw Lewis structures, predict molecular geometry with VSEPR, hybridization and polarity, and intermolecular forces.',
        nameKo: '화학 결합',
        keywords: ['chemical bond', 'ionic', 'covalent', 'lewis structure', 'vsepr', 'molecular geometry', 'hybridization', 'polarity', 'intermolecular'],
      },
      {
        name: 'Gases & Thermochemistry',
        objectives: 'Apply gas laws and kinetic molecular theory; measure and calculate enthalpy changes with calorimetry and Hess\'s law.',
        nameKo: '기체와 열화학',
        keywords: ['gas law', 'ideal gas', 'kinetic molecular', 'thermochemistry', 'enthalpy', 'calorimetry', "hess's law"],
      },
    ],
    textbooks: ['Zumdahl', 'Central Science', 'Tro', 'OpenStax Chemistry', 'Chang'],
  },
  phys1: {
    level: 'Calculus-based mechanics for science and engineering majors.',
    area: 'science',
    category: 'major',
    description: 'Calculus-based mechanics: kinematics, forces, energy, momentum and rotation.',
    units: [
      {
        name: 'Kinematics',
        objectives: 'Describe motion in one and two dimensions with vectors, including projectile motion, using calculus where appropriate.',
        nameKo: '운동학',
        keywords: ['kinematics', 'displacement', 'velocity', 'acceleration', 'projectile', 'motion in one dimension', 'vector'],
      },
      {
        name: "Newton's Laws",
        objectives: 'Apply Newton\'s laws with free-body diagrams to problems involving friction, tension and circular motion.',
        nameKo: '뉴턴 법칙',
        keywords: ["newton's law", 'force', 'friction', 'free body diagram', 'circular motion', 'tension'],
      },
      {
        name: 'Energy & Momentum',
        objectives: 'Use work-energy theorem, conservation of energy, impulse and conservation of momentum, including collisions.',
        nameKo: '에너지와 운동량',
        keywords: ['work', 'kinetic energy', 'potential energy', 'conservation of energy', 'momentum', 'impulse', 'collision'],
      },
      {
        name: 'Rotation & Oscillation',
        objectives: 'Analyze rotational motion, torque, moment of inertia and angular momentum; simple harmonic motion; gravitation.',
        nameKo: '회전과 진동',
        keywords: ['rotation', 'torque', 'angular momentum', 'moment of inertia', 'rolling', 'oscillation', 'simple harmonic', 'gravitation'],
      },
    ],
    textbooks: ['Halliday', 'Serway', 'University Physics', 'Giancoli', 'Knight'],
  },
  cs1: {
    level: 'First programming course for computer science majors.',
    area: 'cs',
    category: 'major',
    description: 'Introduction to programming: control flow, functions, recursion and data abstraction.',
    units: [
      {
        name: 'Programming Basics',
        objectives: 'Write programs using variables, data types, expressions, operators and input/output in a high-level language.',
        nameKo: '프로그래밍 기초',
        keywords: ['variable', 'expression', 'data type', 'operator', 'input', 'python', 'programming'],
      },
      {
        name: 'Control Flow',
        objectives: 'Control program execution with boolean logic, conditionals and loops.',
        nameKo: '제어 구조',
        keywords: ['conditional', 'if statement', 'loop', 'while loop', 'for loop', 'boolean', 'iteration'],
      },
      {
        name: 'Functions & Recursion',
        objectives: 'Decompose problems into functions with parameters and return values; understand scope; write recursive and higher-order functions.',
        nameKo: '함수와 재귀',
        keywords: ['function', 'parameter', 'return value', 'scope', 'recursion', 'higher-order function', 'lambda'],
      },
      {
        name: 'Data & Objects',
        objectives: 'Use built-in data structures (lists, strings, dictionaries), files and exceptions; define simple classes.',
        nameKo: '자료형과 객체',
        keywords: ['list', 'string', 'dictionary', 'tuple', 'file', 'object-oriented', 'class', 'exception'],
      },
    ],
    textbooks: ['Think Python', 'Starting Out with Python', 'Zelle', 'Composing Programs', 'Automate the Boring Stuff'],
  },
  ds: {
    level: 'Second programming course on data structures; requires CS1.',
    area: 'cs',
    category: 'major',
    description: 'Abstract data types, asymptotic analysis, trees, hashing, sorting and graphs.',
    units: [
      {
        name: 'Algorithm Analysis',
        objectives: 'Analyze running time with asymptotic (Big-O) notation and compare algorithm efficiency.',
        nameKo: '알고리즘 분석',
        keywords: ['big-o', 'asymptotic', 'complexity', 'runtime analysis', 'time complexity'],
      },
      {
        name: 'Linear Structures',
        objectives: 'Implement and use linked lists, stacks, queues and dynamic arrays as abstract data types.',
        nameKo: '선형 자료구조',
        keywords: ['linked list', 'stack', 'queue', 'array list', 'dynamic array', 'deque'],
      },
      {
        name: 'Trees & Hashing',
        objectives: 'Implement binary search trees, balanced trees, heaps/priority queues and hash tables.',
        nameKo: '트리와 해싱',
        keywords: ['binary tree', 'binary search tree', 'balanced tree', 'heap', 'priority queue', 'hash table', 'hashing', 'avl', 'red-black'],
      },
      {
        name: 'Sorting & Graphs',
        objectives: 'Implement and analyze sorting algorithms; represent graphs and run BFS, DFS and shortest-path algorithms.',
        nameKo: '정렬과 그래프',
        keywords: ['sorting', 'merge sort', 'quicksort', 'graph', 'breadth-first search', 'depth-first search', 'shortest path'],
      },
    ],
    textbooks: ['Goodrich', 'Weiss', 'Sedgewick', 'Cormen', 'Data Structures and Algorithms'],
  },
  discrete: {
    level: 'Discrete mathematics for computer science majors, proof-based.',
    area: 'math',
    category: 'major',
    description: 'Logic, proofs, sets, counting, probability, number theory and graph theory.',
    units: [
      {
        name: 'Logic & Proofs',
        objectives: 'Use propositional and predicate logic and write proofs by direct argument, contradiction and induction.',
        nameKo: '논리와 증명',
        keywords: ['propositional logic', 'predicate logic', 'quantifier', 'proof', 'induction', 'contradiction', 'truth table'],
      },
      {
        name: 'Sets, Functions & Relations',
        objectives: 'Reason formally about sets, functions, relations, equivalence relations and cardinality.',
        nameKo: '집합·함수·관계',
        keywords: ['set', 'function', 'relation', 'equivalence relation', 'cardinality'],
      },
      {
        name: 'Counting & Probability',
        objectives: 'Solve counting problems with permutations, combinations, pigeonhole and inclusion-exclusion; discrete probability; recurrences.',
        nameKo: '경우의 수와 확률',
        keywords: ['counting', 'permutation', 'combination', 'pigeonhole', 'binomial', 'probability', 'inclusion-exclusion', 'recurrence'],
      },
      {
        name: 'Number Theory & Graphs',
        objectives: 'Apply modular arithmetic, divisibility and primes (e.g. RSA); basic graph theory and trees.',
        nameKo: '정수론과 그래프',
        keywords: ['number theory', 'modular arithmetic', 'divisibility', 'prime', 'gcd', 'graph theory', 'tree', 'rsa'],
      },
    ],
    textbooks: ['Rosen', 'Epp', 'Mathematics for Computer Science'],
  },
  stats: {
    level: 'Introductory (non-calculus) statistics.',
    area: 'math',
    category: 'ge',
    description: 'Descriptive statistics, probability, statistical inference and regression.',
    units: [
      {
        name: 'Descriptive Statistics',
        objectives: 'Summarize data with measures of center and spread and graphical displays; understand sampling and study design.',
        nameKo: '기술통계',
        keywords: ['descriptive statistic', 'mean', 'median', 'standard deviation', 'histogram', 'boxplot', 'sampling'],
      },
      {
        name: 'Probability Models',
        objectives: 'Use probability rules, random variables, binomial and normal distributions, sampling distributions and the Central Limit Theorem.',
        nameKo: '확률 모형',
        keywords: ['probability', 'random variable', 'normal distribution', 'binomial distribution', 'central limit theorem', 'sampling distribution'],
      },
      {
        name: 'Statistical Inference',
        objectives: 'Construct confidence intervals and conduct hypothesis tests (z, t, chi-square) and interpret p-values.',
        nameKo: '통계적 추론',
        keywords: ['confidence interval', 'hypothesis test', 'p-value', 't-test', 'significance', 'chi-square', 'null hypothesis'],
      },
      {
        name: 'Regression',
        objectives: 'Measure correlation and fit and interpret simple linear regression models; introduction to ANOVA.',
        nameKo: '회귀분석',
        keywords: ['correlation', 'linear regression', 'scatterplot', 'least squares', 'residual', 'anova'],
      },
    ],
    textbooks: ['OpenIntro', 'Basic Practice of Statistics', 'Freedman', 'Triola', 'De Veaux'],
  },
  micro: {
    level: 'Introductory microeconomics.',
    area: 'social',
    category: 'ge',
    description: 'Supply and demand, consumer and firm behavior, market structures and welfare.',
    units: [
      {
        name: 'Supply & Demand',
        objectives: 'Analyze market equilibrium with supply and demand, elasticity and price controls.',
        nameKo: '수요와 공급',
        keywords: ['supply', 'demand', 'equilibrium', 'elasticity', 'price control', 'price ceiling', 'price floor'],
      },
      {
        name: 'Consumers & Firms',
        objectives: 'Model consumer choice and utility; analyze production and cost curves, marginal and opportunity cost.',
        nameKo: '소비자와 기업',
        keywords: ['consumer choice', 'utility', 'production', 'cost curve', 'marginal cost', 'opportunity cost'],
      },
      {
        name: 'Market Structures',
        objectives: 'Compare perfect competition, monopoly, oligopoly and monopolistic competition; introductory game theory.',
        nameKo: '시장 구조',
        keywords: ['perfect competition', 'monopoly', 'oligopoly', 'monopolistic competition', 'game theory'],
      },
      {
        name: 'Welfare & Policy',
        objectives: 'Evaluate consumer and producer surplus, taxes and deadweight loss, externalities and public goods.',
        nameKo: '후생과 정책',
        keywords: ['consumer surplus', 'producer surplus', 'externality', 'public good', 'market failure', 'tax', 'deadweight loss'],
      },
    ],
    textbooks: ['Mankiw', 'Krugman', 'OpenStax Microeconomics', 'Case', 'Principles of Microeconomics'],
  },
  macro: {
    level: 'Introductory macroeconomics.',
    area: 'social',
    category: 'ge',
    description: 'National income, growth, money and banking, monetary and fiscal policy.',
    units: [
      {
        name: 'Measuring the Economy',
        objectives: 'Measure GDP, inflation (CPI) and unemployment.',
        nameKo: '거시경제 지표',
        keywords: ['gdp', 'inflation', 'unemployment', 'consumer price index', 'national income'],
      },
      {
        name: 'Long-run Growth',
        objectives: 'Explain long-run economic growth, productivity, saving and investment.',
        nameKo: '장기 성장',
        keywords: ['economic growth', 'productivity', 'saving', 'investment', 'long run'],
      },
      {
        name: 'Money & Monetary Policy',
        objectives: 'Explain money, banking and the central bank, interest rates and monetary policy.',
        nameKo: '화폐와 통화정책',
        keywords: ['money supply', 'central bank', 'federal reserve', 'interest rate', 'monetary policy', 'banking'],
      },
      {
        name: 'Fiscal Policy & Cycles',
        objectives: 'Analyze business cycles with aggregate demand and supply; fiscal policy and the multiplier; open-economy basics.',
        nameKo: '재정정책과 경기변동',
        keywords: ['fiscal policy', 'aggregate demand', 'aggregate supply', 'business cycle', 'government spending', 'multiplier', 'exchange rate'],
      },
    ],
    textbooks: ['Mankiw', 'Krugman', 'OpenStax Macroeconomics', 'Principles of Macroeconomics'],
  },
  psych: {
    level: 'Introductory survey of psychology.',
    area: 'social',
    category: 'ge',
    description: 'Survey of psychology: biological bases, cognition, development, personality and social behavior.',
    units: [
      {
        name: 'Research & Biological Bases',
        objectives: 'Explain psychological research methods and the biological bases of behavior (neurons, brain, nervous system).',
        nameKo: '연구 방법과 생물학적 기초',
        keywords: ['research method', 'experiment', 'neuron', 'brain', 'nervous system', 'biological psychology'],
      },
      {
        name: 'Perception, Learning & Memory',
        objectives: 'Describe sensation and perception, classical and operant conditioning, memory and cognition.',
        nameKo: '지각·학습·기억',
        keywords: ['sensation', 'perception', 'learning', 'classical conditioning', 'operant conditioning', 'memory', 'cognition'],
      },
      {
        name: 'Development & Personality',
        objectives: 'Describe lifespan development, personality theories, intelligence, motivation and emotion.',
        nameKo: '발달과 성격',
        keywords: ['development', 'personality', 'intelligence', 'motivation', 'emotion'],
      },
      {
        name: 'Social & Clinical',
        objectives: 'Explain social psychology, consciousness, stress, psychological disorders and therapies.',
        nameKo: '사회·임상 심리',
        keywords: ['social psychology', 'psychological disorder', 'therapy', 'stress', 'mental health', 'consciousness'],
      },
    ],
    textbooks: ['Myers', 'OpenStax Psychology', 'Gray', 'Ciccarelli'],
  },
  writing: {
    level: 'First-year college composition.',
    area: 'humanities',
    category: 'ge',
    description: 'Academic reading and writing: rhetoric, argument, revision and research.',
    units: [
      {
        name: 'Rhetoric & Argument',
        objectives: 'Analyze rhetorical situations (audience, purpose) and compose thesis-driven arguments.',
        nameKo: '수사학과 논증',
        keywords: ['rhetoric', 'rhetorical analysis', 'audience', 'argument', 'thesis', 'persuasive'],
      },
      {
        name: 'Writing Process',
        objectives: 'Draft, peer review and substantially revise multiple academic essays.',
        nameKo: '글쓰기 과정',
        keywords: ['drafting', 'revision', 'peer review', 'writing process', 'essay'],
      },
      {
        name: 'Research Writing',
        objectives: 'Find, evaluate and integrate sources with correct citation (MLA/APA) in a research-based paper.',
        nameKo: '연구 기반 글쓰기',
        keywords: ['research paper', 'source', 'citation', 'mla', 'apa', 'annotated bibliography', 'plagiarism'],
      },
      {
        name: 'Critical Reading',
        objectives: 'Read complex texts closely and critically; summarize and analyze arguments.',
        nameKo: '비판적 읽기',
        keywords: ['critical reading', 'close reading', 'critical thinking', 'summary', 'analysis'],
      },
    ],
    textbooks: ['They Say', "St. Martin's Guide", "Everything's an Argument", 'Norton Field Guide'],
  },
  bio1: {
    level: 'First semester of the introductory biology sequence for majors.',
    area: 'science',
    category: 'major',
    description: 'Molecules and cells, genetics, and evolution.',
    units: [
      {
        name: 'Chemistry of Life',
        objectives: 'Explain the structure and function of biological macromolecules and enzymes.',
        nameKo: '생명의 화학',
        keywords: ['macromolecule', 'protein', 'carbohydrate', 'lipid', 'nucleic acid', 'enzyme'],
      },
      {
        name: 'Cell Biology',
        objectives: 'Describe cell structure, membranes and transport, cellular respiration and photosynthesis.',
        nameKo: '세포 생물학',
        keywords: ['cell structure', 'membrane', 'organelle', 'membrane transport', 'cellular respiration', 'photosynthesis'],
      },
      {
        name: 'Genetics',
        objectives: 'Explain DNA replication, transcription, translation, gene expression, mitosis, meiosis and Mendelian inheritance.',
        nameKo: '유전학',
        keywords: ['dna', 'replication', 'transcription', 'translation', 'gene expression', 'mitosis', 'meiosis', 'mendelian', 'inheritance'],
      },
      {
        name: 'Evolution & Ecology',
        objectives: 'Explain natural selection, population genetics, phylogeny, speciation and basic ecology.',
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
      level: t.level,
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
