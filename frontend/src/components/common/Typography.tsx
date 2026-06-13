import React from 'react';

// ============================================================================
// Heading Component
// ============================================================================
export type HeadingVariant = 'h1' | 'h2' | 'h3' | 'h4';

interface HeadingProps extends React.HTMLAttributes<HTMLHeadingElement> {
  variant?: HeadingVariant;
  children: React.ReactNode;
}

const headingStyles: Record<HeadingVariant, string> = {
  h1: 'text-2xl md:text-3xl font-black text-slate-800 tracking-tight',
  h2: 'text-xl md:text-2xl font-black text-slate-800 tracking-tight',
  h3: 'text-lg md:text-xl font-bold text-slate-800',
  h4: 'text-base md:text-lg font-bold text-slate-800',
};

export const Heading: React.FC<HeadingProps> = ({ variant = 'h1', className = '', children, ...props }) => {
  const Component = variant;
  return (
    <Component className={`${headingStyles[variant]} ${className}`} {...props}>
      {children}
    </Component>
  );
};

// ============================================================================
// Text Component
// ============================================================================
export type TextVariant = 'body' | 'small' | 'caption';

interface TextProps extends React.HTMLAttributes<HTMLParagraphElement> {
  variant?: TextVariant;
  children: React.ReactNode;
}

const textStyles: Record<TextVariant, string> = {
  body: 'text-sm md:text-base text-slate-600 font-normal',
  small: 'text-xs md:text-sm text-slate-500 font-medium',
  caption: 'text-[10px] md:text-xs text-slate-400 font-bold',
};

export const Text: React.FC<TextProps> = ({ variant = 'body', className = '', children, ...props }) => {
  // Use span for caption to allow easier inline use if needed, else p
  const Component = variant === 'caption' ? 'span' : 'p';
  return (
    <Component className={`${textStyles[variant]} ${className}`} {...props}>
      {children}
    </Component>
  );
};

// ============================================================================
// Label Component
// ============================================================================
export type LabelVariant = 'form' | 'badge';

interface LabelProps extends React.HTMLAttributes<HTMLSpanElement | HTMLLabelElement> {
  variant?: LabelVariant;
  htmlFor?: string; // For form labels
  children: React.ReactNode;
}

const labelStyles: Record<LabelVariant, string> = {
  form: 'text-xs md:text-sm font-bold text-slate-700',
  badge: 'text-[10px] md:text-xs font-bold uppercase tracking-wider',
};

export const Label: React.FC<LabelProps> = ({ variant = 'form', className = '', children, htmlFor, ...props }) => {
  if (variant === 'form') {
    return (
      <label htmlFor={htmlFor} className={`${labelStyles[variant]} ${className}`} {...(props as React.LabelHTMLAttributes<HTMLLabelElement>)}>
        {children}
      </label>
    );
  }

  return (
    <span className={`${labelStyles[variant]} ${className}`} {...props}>
      {children}
    </span>
  );
};
