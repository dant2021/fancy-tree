export interface Props extends Base<string>, Other {
  name: string;
  render(value: string): void;
}

export function Widget(props: Props) {
  return <div className="widget">Hello {props.name}</div>;
}

export const ArrowWidget = ({ name }: Props) => <span>{name}</span>;
